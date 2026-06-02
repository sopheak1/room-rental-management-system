package com.rentalprint.bridge;

import android.Manifest;
import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public class MainActivity extends AppCompatActivity {

    private static final int REQUEST_BLUETOOTH = 1;
    static final String PREFS       = "PrintBridgePrefs";
    static final String PREF_DEVICE = "selected_device";
    static final String PREF_URL    = "server_url";
    static final String DEFAULT_URL = "http://192.168.50.24:8080";

    private WebView webView;
    private TextView tvBridgeStatus;
    private BluetoothAdapter bluetoothAdapter;
    SharedPreferences prefs;
    PrintServer printServer;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView        = findViewById(R.id.webView);
        tvBridgeStatus = findViewById(R.id.tvBridgeStatus);

        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setBuiltInZoomControls(false);
        // Keep ALL links (including target="_blank") inside the app
        ws.setSupportMultipleWindows(false);
        ws.setJavaScriptCanOpenWindowsAutomatically(false);

        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        webView.addJavascriptInterface(new AndroidBridge(), "Android");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                String scheme = req.getUrl().getScheme();
                // Keep ALL http/https links inside the WebView
                if ("http".equals(scheme) || "https".equals(scheme)) return false;
                // Only send non-web schemes (tel:, mailto:) to external apps
                try { startActivity(new Intent(Intent.ACTION_VIEW, req.getUrl())); } catch (Exception ignored) {}
                return true;
            }
            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError err) {
                handler.proceed();
            }
        });

        // Handle target="_blank" links — open in same WebView instead of browser
        webView.setWebChromeClient(new android.webkit.WebChromeClient() {
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog,
                                          boolean isUserGesture, android.os.Message resultMsg) {
                // Get the URL from the hit test result and load it in the current WebView
                WebView.HitTestResult result = view.getHitTestResult();
                String url = result.getExtra();
                if (url != null) view.loadUrl(url);
                return false;
            }
        });

        loadWebApp();
        startBridge();

        findViewById(R.id.btnSettings).setOnClickListener(v -> showSettingsDialog());
        findViewById(R.id.btnReload).setOnClickListener(v -> loadWebApp());
    }

    private void loadWebApp() {
        webView.loadUrl(prefs.getString(PREF_URL, DEFAULT_URL));
    }

    void startBridge() {
        if (printServer != null && printServer.isRunning()) return;
        String deviceAddr = prefs.getString(PREF_DEVICE, null);
        if (deviceAddr == null) return;
        String serverUrl = prefs.getString(PREF_URL, DEFAULT_URL);
        printServer = new PrintServer(9100, deviceAddr, serverUrl, bluetoothAdapter, count ->
                runOnUiThread(() -> tvBridgeStatus.setText("🟢 Bridge · " + count + " printed")));
        try {
            printServer.start();
            tvBridgeStatus.setText("🟢 Bridge ready");
            tvBridgeStatus.setTextColor(0xFF16A34A);
        } catch (IOException e) {
            tvBridgeStatus.setText("🔴 Bridge error");
            tvBridgeStatus.setTextColor(0xFFDC2626);
        }
    }

    private void stopBridge() {
        if (printServer != null) { printServer.stopServer(); printServer = null; }
        tvBridgeStatus.setText("🔴 Stopped");
        tvBridgeStatus.setTextColor(0xFFDC2626);
    }

    // ── JavaScript → Native bridge ─────────────────────────────
    private class AndroidBridge {

        @JavascriptInterface
        public void print(int receiptId) {
            String serverUrl = prefs.getString(PREF_URL, DEFAULT_URL);
            doPrint(receiptId, serverUrl + "/receipts/" + receiptId + "/print?bridge=1");
        }

        @JavascriptInterface
        public void printTable(int receiptId) {
            String serverUrl = prefs.getString(PREF_URL, DEFAULT_URL);
            doPrint(receiptId, serverUrl + "/receipts/" + receiptId + "/print_table?bridge=1");
        }

        private void doPrint(int receiptId, String printUrl) {
            runOnUiThread(() ->
                webView.evaluateJavascript("showBridgePrinting()", null));

            new Thread(() -> {
                try {
                    // Step 1: render to bitmap
                    Bitmap bmp = renderUrlToBitmap(printUrl);

                    // Step 2: show preview dialog — user confirms before printing
                    CountDownLatch confirm = new CountDownLatch(1);
                    boolean[] doPrint = {false};

                    runOnUiThread(() -> showPreviewDialog(bmp,
                        () -> { doPrint[0] = true;  confirm.countDown(); },   // Print
                        () -> { doPrint[0] = false; confirm.countDown(); }    // Cancel
                    ));

                    confirm.await(60, TimeUnit.SECONDS); // wait for user choice

                    if (doPrint[0]) {
                        // Step 3: convert + send
                        byte[] escpos = EscPosConverter.bitmapToEscPos(bmp);
                        bmp.recycle();
                        sendViaBluetooth(escpos);
                        runOnUiThread(() ->
                            webView.evaluateJavascript("showBridgeSuccess()", null));
                    } else {
                        bmp.recycle();
                        runOnUiThread(() ->
                            webView.evaluateJavascript("showBridgeError('Cancelled')", null));
                    }

                } catch (Exception e) {
                    String msg = e.getMessage() != null
                        ? e.getMessage().replace("'", "") : "Unknown error";
                    runOnUiThread(() ->
                        webView.evaluateJavascript("showBridgeError('" + msg + "')", null));
                }
            }).start();
        }

        @JavascriptInterface
        public boolean isAvailable() { return true; }
    }

    // ── Preview dialog ─────────────────────────────────────────
    private void showPreviewDialog(Bitmap bitmap, Runnable onPrint, Runnable onCancel) {
        android.widget.ScrollView scroll = new android.widget.ScrollView(this);
        android.widget.ImageView img = new android.widget.ImageView(this);
        img.setImageBitmap(bitmap);
        // Scale image to dialog width, scroll vertically for height
        img.setScaleType(android.widget.ImageView.ScaleType.FIT_CENTER);
        img.setAdjustViewBounds(true);
        img.setPadding(8, 8, 8, 8);
        // Constrain to dialog width so right side is not clipped
        scroll.setFillViewport(true);
        scroll.addView(img, new android.widget.LinearLayout.LayoutParams(
            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
            android.view.ViewGroup.LayoutParams.WRAP_CONTENT));

        new AlertDialog.Builder(this)
            .setTitle("👁 Receipt Preview — OK to print?")
            .setView(scroll)
            .setPositiveButton("🖨️ Print", (d, w) -> onPrint.run())
            .setNegativeButton("✕ Cancel",  (d, w) -> onCancel.run())
            .setOnCancelListener(d -> onCancel.run())
            .show();
    }

    // ── Render any print URL via hidden WebView → Bitmap ───────
    private Bitmap renderUrlToBitmap(String printUrl) throws Exception {
        String serverUrl = prefs.getString(PREF_URL, DEFAULT_URL);

        CountDownLatch latch  = new CountDownLatch(1);
        Bitmap[]    result    = {null};
        Exception[] renderErr = {null};

        runOnUiThread(() -> {
            try {
                @SuppressLint("SetJavaScriptEnabled")
                WebView pv = new WebView(MainActivity.this);
                WebSettings s = pv.getSettings();
                s.setJavaScriptEnabled(true);
                s.setDomStorageEnabled(true);
                // Force 58mm (220px) viewport — prevent phone-width rendering
                s.setUseWideViewPort(false);
                s.setLoadWithOverviewMode(false);
                s.setTextZoom(100);
                s.setDefaultFontSize(13);
                s.setDefaultFixedFontSize(13);

                // CRITICAL: software rendering so view.draw(canvas) captures content
                pv.setLayerType(View.LAYER_TYPE_SOFTWARE, null);
                // Hide native scrollbars so they don't appear in the screenshot
                pv.setVerticalScrollBarEnabled(false);
                pv.setHorizontalScrollBarEnabled(false);
                pv.setScrollBarStyle(View.SCROLLBARS_OUTSIDE_OVERLAY);

                // Viewport is width=220 (58mm) → physical px = 220 × device density
                float density = getResources().getDisplayMetrics().density;
                int pxWidth = Math.round(220 * density);

                // CRITICAL: attach to window so WebView actually renders
                android.view.ViewGroup root = (android.view.ViewGroup)
                    getWindow().getDecorView().getRootView();
                android.view.ViewGroup.LayoutParams lp = new android.view.ViewGroup.LayoutParams(
                    pxWidth, android.view.ViewGroup.LayoutParams.WRAP_CONTENT);
                pv.setVisibility(View.INVISIBLE);
                root.addView(pv, lp);

                // Share session cookie
                String cookie = CookieManager.getInstance().getCookie(serverUrl);
                if (cookie != null) CookieManager.getInstance().setCookie(serverUrl, cookie);
                CookieManager.getInstance().setAcceptThirdPartyCookies(pv, true);

                pv.setWebViewClient(new WebViewClient() {
                    @Override
                    public void onPageFinished(WebView view, String url) {
                        if (!url.contains("/print")) return;
                        // Wait 3s for Noto Sans Khmer to load
                        view.postDelayed(() -> {
                            try {
                                // getContentHeight returns CSS px → convert to physical px
                                int cssH = view.getContentHeight();
                                if (cssH <= 0) cssH = 2000;
                                int pxHeight = Math.round(cssH * density);

                                view.measure(
                                    View.MeasureSpec.makeMeasureSpec(pxWidth, View.MeasureSpec.EXACTLY),
                                    View.MeasureSpec.makeMeasureSpec(pxHeight, View.MeasureSpec.EXACTLY)
                                );
                                view.layout(0, 0, pxWidth, pxHeight);

                                // Bitmap at full physical resolution — captures all content
                                Bitmap bmp = Bitmap.createBitmap(pxWidth, pxHeight, Bitmap.Config.ARGB_8888);
                                Canvas cv  = new Canvas(bmp);
                                cv.drawColor(Color.WHITE);
                                view.draw(cv);

                                // EscPosConverter will scale pxWidth → 384 printer dots
                                result[0] = bmp;
                            } catch (Exception e) {
                                renderErr[0] = e;
                            } finally {
                                root.removeView(pv);
                                latch.countDown();
                            }
                        }, 3000);
                    }
                    @Override
                    public void onReceivedSslError(WebView v, SslErrorHandler h, SslError e) {
                        h.proceed();
                    }
                });

                pv.loadUrl(printUrl);

            } catch (Exception e) {
                renderErr[0] = e;
                latch.countDown();
            }
        });

        if (!latch.await(35, TimeUnit.SECONDS))
            throw new IOException("Timed out rendering receipt");
        if (renderErr[0] != null) throw renderErr[0];
        if (result[0] == null)    throw new IOException("Render produced no output");
        return result[0]; // Bitmap
    }

    // ── Bluetooth SPP send ─────────────────────────────────────
    private void sendViaBluetooth(byte[] data) throws IOException {
        String addr = prefs.getString(PREF_DEVICE, null);
        if (addr == null) throw new IOException("No printer selected");
        UUID SPP = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");
        BluetoothDevice device = bluetoothAdapter.getRemoteDevice(addr);
        BluetoothSocket socket = device.createRfcommSocketToServiceRecord(SPP);
        try {
            bluetoothAdapter.cancelDiscovery();
            socket.connect();
            OutputStream out = socket.getOutputStream();
            out.write(data);
            out.flush();
            Thread.sleep(800);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            socket.close();
        }
    }

    // ── Settings dialog ────────────────────────────────────────
    @SuppressLint("InflateParams")
    private void showSettingsDialog() {
        View v = getLayoutInflater().inflate(R.layout.dialog_settings, null);
        EditText etUrl     = v.findViewById(R.id.etUrl);
        TextView tvCurrent = v.findViewById(R.id.tvCurrentUrl);
        TextView tvDevice  = v.findViewById(R.id.tvDeviceAddr);
        TextView tvStatus  = v.findViewById(R.id.tvBridgeStatusDialog);
        Button btnPrinter  = v.findViewById(R.id.btnPickPrinter);
        Button btnBridge   = v.findViewById(R.id.btnToggleBridge);

        String savedUrl = prefs.getString(PREF_URL, DEFAULT_URL);
        etUrl.setText(savedUrl);
        tvCurrent.setText("Current: " + savedUrl);
        String addr = prefs.getString(PREF_DEVICE, null);
        tvDevice.setText(addr != null ? addr : "None selected");
        boolean running = printServer != null && printServer.isRunning();
        tvStatus.setText(running ? "🟢 Running" : "🔴 Stopped");
        btnBridge.setText(running ? "Stop Bridge" : "Start Bridge");

        btnPrinter.setOnClickListener(px -> selectPrinter());
        btnBridge.setOnClickListener(px -> {
            if (printServer != null && printServer.isRunning()) {
                stopBridge(); btnBridge.setText("Start Bridge"); tvStatus.setText("🔴 Stopped");
            } else {
                startBridge();
                boolean r = printServer != null && printServer.isRunning();
                btnBridge.setText(r ? "Stop Bridge" : "Start Bridge");
                tvStatus.setText(r ? "🟢 Running" : "🔴 Error");
            }
        });

        new AlertDialog.Builder(this)
            .setTitle("⚙️ Print Bridge Settings")
            .setView(v)
            .setPositiveButton("Save URL & Reload", (d, w) -> {
                String newUrl = etUrl.getText().toString().trim();
                if (newUrl.endsWith("/")) newUrl = newUrl.substring(0, newUrl.length() - 1);
                if (!TextUtils.isEmpty(newUrl)) {
                    prefs.edit().putString(PREF_URL, newUrl).apply();
                    // Clear old session cookies so login page shows correctly on new server
                    CookieManager.getInstance().removeAllCookies(null);
                    CookieManager.getInstance().flush();
                    stopBridge(); loadWebApp(); startBridge();
                    Toast.makeText(this, "URL saved — please log in", Toast.LENGTH_SHORT).show();
                }
            })
            .setNegativeButton("Close", null)
            .create().show();
    }

    private void selectPrinter() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
                ActivityCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                        != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                new String[]{Manifest.permission.BLUETOOTH_CONNECT,
                             Manifest.permission.BLUETOOTH_SCAN}, REQUEST_BLUETOOTH);
            return;
        }
        if (!bluetoothAdapter.isEnabled()) {
            startActivity(new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)); return;
        }
        Set<BluetoothDevice> paired = bluetoothAdapter.getBondedDevices();
        if (paired.isEmpty()) {
            Toast.makeText(this, "Pair PT-210 first.", Toast.LENGTH_LONG).show(); return;
        }
        List<String> names = new ArrayList<>(), addresses = new ArrayList<>();
        for (BluetoothDevice d : paired) {
            String name = d.getAddress();
            try { name = d.getName(); } catch (SecurityException ignored) {}
            names.add(name + "\n" + d.getAddress());
            addresses.add(d.getAddress());
        }
        new AlertDialog.Builder(this)
            .setTitle("Select Printer")
            .setItems(names.toArray(new String[0]), (dlg, which) -> {
                prefs.edit().putString(PREF_DEVICE, addresses.get(which)).apply();
                stopBridge(); startBridge();
                Toast.makeText(this, "Printer set: " + addresses.get(which), Toast.LENGTH_SHORT).show();
            }).show();
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack(); else super.onBackPressed();
    }

    @Override
    public void onRequestPermissionsResult(int req, String[] perms, int[] results) {
        super.onRequestPermissionsResult(req, perms, results);
        if (req == REQUEST_BLUETOOTH && results.length > 0
                && results[0] == PackageManager.PERMISSION_GRANTED) selectPrinter();
    }
}

package com.rentalprint.bridge;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Dialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
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
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;

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

        // --- WebView setup ---
        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setBuiltInZoomControls(false);

        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        webView.addJavascriptInterface(new AndroidBridge(), "Android");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                String url = req.getUrl().toString();
                String serverUrl = prefs.getString(PREF_URL, DEFAULT_URL);
                // Keep same-server links inside the WebView
                if (url.startsWith(serverUrl)) return false;
                // Open external links in the system browser
                startActivity(new Intent(Intent.ACTION_VIEW, req.getUrl()));
                return true;
            }

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError err) {
                handler.proceed(); // Accept self-signed certs for local dev
            }
        });

        loadWebApp();

        // --- Start print bridge automatically ---
        startBridge();

        findViewById(R.id.btnSettings).setOnClickListener(v -> showSettingsDialog());
        findViewById(R.id.btnReload).setOnClickListener(v -> loadWebApp());
    }

    private void loadWebApp() {
        String url = prefs.getString(PREF_URL, DEFAULT_URL);
        webView.loadUrl(url);
    }

    // ── Bridge auto-start ──────────────────────────────────────
    void startBridge() {
        if (printServer != null && printServer.isRunning()) return;
        String deviceAddr = prefs.getString(PREF_DEVICE, null);
        if (deviceAddr == null) return; // No printer yet — wait for user to configure

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
        tvBridgeStatus.setText("🔴 Bridge stopped");
        tvBridgeStatus.setTextColor(0xFFDC2626);
    }

    // ── Settings dialog ───────────────────────────────────────
    @SuppressLint("InflateParams")
    private void showSettingsDialog() {
        View v = getLayoutInflater().inflate(R.layout.dialog_settings, null);

        EditText etUrl       = v.findViewById(R.id.etUrl);
        TextView tvCurrent   = v.findViewById(R.id.tvCurrentUrl);
        TextView tvDevice    = v.findViewById(R.id.tvDeviceAddr);
        TextView tvStatus    = v.findViewById(R.id.tvBridgeStatusDialog);
        Button   btnPrinter  = v.findViewById(R.id.btnPickPrinter);
        Button   btnBridge   = v.findViewById(R.id.btnToggleBridge);

        String savedUrl = prefs.getString(PREF_URL, DEFAULT_URL);
        etUrl.setText(savedUrl);
        tvCurrent.setText("Current: " + savedUrl);

        String addr = prefs.getString(PREF_DEVICE, null);
        tvDevice.setText(addr != null ? addr : "None selected");
        tvStatus.setText(printServer != null && printServer.isRunning() ? "🟢 Running" : "🔴 Stopped");
        btnBridge.setText(printServer != null && printServer.isRunning() ? "Stop Bridge" : "Start Bridge");

        btnPrinter.setOnClickListener(px -> selectPrinter());
        btnBridge.setOnClickListener(px -> {
            if (printServer != null && printServer.isRunning()) {
                stopBridge();
                btnBridge.setText("Start Bridge");
                tvStatus.setText("🔴 Stopped");
            } else {
                startBridge();
                boolean running = printServer != null && printServer.isRunning();
                btnBridge.setText(running ? "Stop Bridge" : "Start Bridge");
                tvStatus.setText(running ? "🟢 Running" : "🔴 Error");
            }
        });

        AlertDialog dlg = new AlertDialog.Builder(this)
                .setTitle("⚙️ Print Bridge Settings")
                .setView(v)
                .setPositiveButton("Save URL & Reload", (d, w) -> {
                    String newUrl = etUrl.getText().toString().trim();
                    if (newUrl.endsWith("/")) newUrl = newUrl.substring(0, newUrl.length() - 1);
                    if (!TextUtils.isEmpty(newUrl)) {
                        prefs.edit().putString(PREF_URL, newUrl).apply();
                        stopBridge();
                        loadWebApp();
                        startBridge();
                        Toast.makeText(this, "URL saved & reloaded", Toast.LENGTH_SHORT).show();
                    }
                })
                .setNegativeButton("Close", null)
                .create();
        dlg.show();
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
            startActivity(new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE));
            return;
        }
        Set<BluetoothDevice> paired = bluetoothAdapter.getBondedDevices();
        if (paired.isEmpty()) {
            Toast.makeText(this, "No paired devices. Pair PT-210 first.", Toast.LENGTH_LONG).show();
            return;
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
                    stopBridge();
                    startBridge();
                    Toast.makeText(this, "Printer set: " + addresses.get(which), Toast.LENGTH_SHORT).show();
                })
                .show();
    }

    // ── JavaScript → Native bridge ────────────────────────────
    private class AndroidBridge {

        @JavascriptInterface
        public void print(int receiptId) {
            // Show spinner in WebView
            runOnUiThread(() ->
                webView.evaluateJavascript("showBridgePrinting()", null));

            new Thread(() -> {
                try {
                    byte[] data = fetchEscPos(receiptId);
                    sendViaBluetooth(data);
                    runOnUiThread(() ->
                        webView.evaluateJavascript("showBridgeSuccess()", null));
                } catch (Exception e) {
                    runOnUiThread(() ->
                        webView.evaluateJavascript(
                            "showBridgeError('" + e.getMessage().replace("'","") + "')", null));
                }
            }).start();
        }

        @JavascriptInterface
        public boolean isAvailable() { return true; }
    }

    private byte[] fetchEscPos(int receiptId) throws IOException {
        String serverUrl = prefs.getString(PREF_URL, DEFAULT_URL);
        String endpoint  = serverUrl + "/receipts/" + receiptId + "/escpos";
        String cookie    = CookieManager.getInstance().getCookie(serverUrl);

        HttpURLConnection conn = (HttpURLConnection) new URL(endpoint).openConnection();
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(30000);
        if (cookie != null) conn.setRequestProperty("Cookie", cookie);

        if (conn.getResponseCode() != 200) {
            throw new IOException("Server returned " + conn.getResponseCode());
        }

        InputStream is = conn.getInputStream();
        byte[] buf = is.readAllBytes();
        conn.disconnect();
        return buf;
    }

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
            Thread.sleep(500);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            socket.close();
        }
    }

    // ── Navigation ────────────────────────────────────────────
    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override
    public void onRequestPermissionsResult(int req, String[] perms, int[] results) {
        super.onRequestPermissionsResult(req, perms, results);
        if (req == REQUEST_BLUETOOTH && results.length > 0
                && results[0] == PackageManager.PERMISSION_GRANTED) selectPrinter();
    }
}

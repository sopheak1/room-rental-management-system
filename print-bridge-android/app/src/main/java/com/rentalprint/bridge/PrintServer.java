package com.rentalprint.bridge;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.UUID;
import fi.iki.elonen.NanoHTTPD;

public class PrintServer extends NanoHTTPD {

    private static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");

    private final String deviceAddress;
    private final String serverUrl;
    private final BluetoothAdapter bluetoothAdapter;
    private final PrintCallback callback;
    private int jobCount = 0;

    public interface PrintCallback {
        void onJobComplete(int totalJobs);
    }

    public PrintServer(int port, String deviceAddress, String serverUrl,
                       BluetoothAdapter adapter, PrintCallback cb) {
        super(port);
        this.deviceAddress = deviceAddress;
        this.serverUrl = serverUrl;
        this.bluetoothAdapter = adapter;
        this.callback = cb;
    }

    @Override
    public Response serve(IHTTPSession session) {
        if (Method.OPTIONS.equals(session.getMethod())) {
            return corsResponse(newFixedLengthResponse(""));
        }

        if (!Method.POST.equals(session.getMethod()) || !"/print".equals(session.getUri())) {
            return corsResponse(newFixedLengthResponse(Response.Status.NOT_FOUND, "text/plain", "Not found"));
        }

        try {
            int contentLength = Integer.parseInt(
                    session.getHeaders().getOrDefault("content-length", "0"));
            if (contentLength <= 0) {
                return corsResponse(newFixedLengthResponse(
                        Response.Status.BAD_REQUEST, "text/plain", "Empty body"));
            }
            byte[] escposData = new byte[contentLength];
            InputStream is = session.getInputStream();
            int read = 0;
            while (read < contentLength) {
                int r = is.read(escposData, read, contentLength - read);
                if (r < 0) break;
                read += r;
            }

            sendToPrinter(escposData);
            jobCount++;
            if (callback != null) callback.onJobComplete(jobCount);
            return corsResponse(newFixedLengthResponse(Response.Status.OK, "text/plain", "OK"));

        } catch (Exception e) {
            return corsResponse(newFixedLengthResponse(Response.Status.INTERNAL_ERROR,
                    "text/plain", "Print error: " + e.getMessage()));
        }
    }

    private void sendToPrinter(byte[] data) throws IOException {
        BluetoothDevice device = bluetoothAdapter.getRemoteDevice(deviceAddress);
        BluetoothSocket socket = device.createRfcommSocketToServiceRecord(SPP_UUID);
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

    private Response corsResponse(Response r) {
        r.addHeader("Access-Control-Allow-Origin", "*");
        r.addHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
        r.addHeader("Access-Control-Allow-Headers", "Content-Type");
        return r;
    }

    public void stopServer() { stop(); }

    public boolean isRunning() { return wasStarted(); }

    public String getServerUrl() { return serverUrl; }
}

package com.rentalprint.bridge;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorMatrix;
import android.graphics.ColorMatrixColorFilter;
import android.graphics.Paint;
import java.io.ByteArrayOutputStream;
import java.io.IOException;

public class EscPosConverter {

    // PT-210: 48mm print width at 203 DPI = 384 dots
    private static final int PRINTER_DOTS = 384;
    // Bottom padding rows after last content row
    private static final int BOTTOM_PADDING = 60;

    public static byte[] bitmapToEscPos(Bitmap original) throws IOException {
        // 1. Convert to grayscale
        Bitmap gray = toGrayscale(original);

        // 2. Scale to full printer width (384 dots), maintain aspect ratio
        int scaledH = (int) (gray.getHeight() * ((float) PRINTER_DOTS / gray.getWidth()));
        Bitmap scaled = Bitmap.createScaledBitmap(gray, PRINTER_DOTS, scaledH, true);
        gray.recycle();

        // 3. Crop trailing white space + add small bottom padding
        scaled = cropAndPad(scaled);

        // 4. Build ESC/POS bytes
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int widthBytes = PRINTER_DOTS / 8; // 48 bytes per row
        int height     = scaled.getHeight();

        // Initialize printer
        out.write(new byte[]{0x1B, 0x40});       // ESC @ — reset
        out.write(new byte[]{0x1B, 0x33, 0x00}); // ESC 3 0 — minimal line spacing

        // GS v 0 — raster bit image
        // Bytes: 1D 76 30 m xL xH yL yH [data]
        out.write(0x1D); // GS
        out.write(0x76); // v
        out.write(0x30); // 0
        out.write(0x00); // m=0 normal density
        out.write(widthBytes & 0xFF);        // xL
        out.write((widthBytes >> 8) & 0xFF); // xH
        out.write(height & 0xFF);            // yL
        out.write((height >> 8) & 0xFF);     // yH

        // Pixel data: 1 = black, 0 = white, MSB = leftmost dot
        for (int y = 0; y < height; y++) {
            for (int xB = 0; xB < widthBytes; xB++) {
                int b = 0;
                for (int bit = 0; bit < 8; bit++) {
                    int x = xB * 8 + bit;
                    if (x < PRINTER_DOTS) {
                        int px  = scaled.getPixel(x, y);
                        int lum = (Color.red(px) + Color.green(px) + Color.blue(px)) / 3;
                        if (lum < 180) { // threshold — 180 eliminates antialiasing grey
                            b |= (0x80 >> bit);
                        }
                    }
                }
                out.write(b);
            }
        }

        scaled.recycle();

        // Feed 3 lines then cut
        out.write(new byte[]{0x1B, 0x64, 0x03}); // ESC d 3 — feed 3 lines
        out.write(new byte[]{0x1D, 0x56, 0x00}); // GS V 0  — full cut

        return out.toByteArray();
    }

    // ── Helpers ───────────────────────────────────────────────

    private static Bitmap toGrayscale(Bitmap src) {
        Bitmap out   = Bitmap.createBitmap(src.getWidth(), src.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas c     = new Canvas(out);
        Paint  paint = new Paint();
        ColorMatrix cm = new ColorMatrix();
        cm.setSaturation(0);
        paint.setColorFilter(new ColorMatrixColorFilter(cm));
        // Fill white background first (in case of transparency)
        c.drawColor(Color.WHITE);
        c.drawBitmap(src, 0, 0, paint);
        return out;
    }

    private static Bitmap cropAndPad(Bitmap bmp) {
        int lastRow = 0;
        for (int y = bmp.getHeight() - 1; y >= 0; y--) {
            for (int x = 0; x < bmp.getWidth(); x++) {
                int px  = bmp.getPixel(x, y);
                int lum = (Color.red(px) + Color.green(px) + Color.blue(px)) / 3;
                if (lum < 230) { // found non-white pixel
                    lastRow = y;
                    break;
                }
            }
            if (lastRow > 0) break;
        }
        int newH = Math.min(lastRow + BOTTOM_PADDING, bmp.getHeight());
        Bitmap cropped = Bitmap.createBitmap(bmp, 0, 0, bmp.getWidth(), newH);
        bmp.recycle();
        return cropped;
    }
}

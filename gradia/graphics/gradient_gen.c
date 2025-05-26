// Copyright (C) 2025 Alexander Vanhee
//
// This program is free software: you can redistribute it and/or modify it
// under the terms of the GNU General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option)
// any later version.
//
// This program is distributed in the hope that it will be useful, but WITHOUT
// ANY WARRANTY; without even the implied warranty of  MERCHANTABILITY or
// FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
// more details.
//
// You should have received a copy of the GNU General Public License along with
// this program.  If not, see <http://www.gnu.org/licenses/>.

#include <math.h>
#include <stdint.h>

void generate_gradient(uint8_t* pixels, int width, int height,
                      int start_r, int start_g, int start_b,
                      int end_r, int end_g, int end_b,
                      double angle) {
    double cos_angle = cos(angle * M_PI / 180.0);
    double sin_angle = sin(angle * M_PI / 180.0);

    double corners[4];
    corners[0] = 0 * cos_angle + 0 * sin_angle;
    corners[1] = (width-1) * cos_angle + 0 * sin_angle;
    corners[2] = 0 * cos_angle + (height-1) * sin_angle;
    corners[3] = (width-1) * cos_angle + (height-1) * sin_angle;

    double min_coord = corners[0];
    double max_coord = corners[0];
    for (int i = 1; i < 4; i++) {
        if (corners[i] < min_coord) min_coord = corners[i];
        if (corners[i] > max_coord) max_coord = corners[i];
    }

    double range = max_coord - min_coord;
    if (range == 0) range = 1.0;

    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            double coord = x * cos_angle + y * sin_angle;
            double t = (coord - min_coord) / range;

            // Clamp t to [0, 1]
            if (t < 0) t = 0;
            if (t > 1) t = 1;

            int idx = (y * width + x) * 4;
            pixels[idx] = (uint8_t)(start_r + (end_r - start_r) * t);     // R
            pixels[idx + 1] = (uint8_t)(start_g + (end_g - start_g) * t); // G
            pixels[idx + 2] = (uint8_t)(start_b + (end_b - start_b) * t); // B
            pixels[idx + 3] = 255;                                        // A
        }
    }
}


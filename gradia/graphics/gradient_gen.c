#include <math.h>
#include <stdint.h>

typedef struct {
    double position; // 0.0 to 1.0
    uint8_t r, g, b;
} ColorStop;

static void interpolate_color(double t, const ColorStop* stops, int num_stops, uint8_t* out_r, uint8_t* out_g, uint8_t* out_b) {
    if (t <= stops[0].position) {
        *out_r = stops[0].r;
        *out_g = stops[0].g;
        *out_b = stops[0].b;
        return;
    }
    for (int i = 1; i < num_stops; i++) {
        if (t <= stops[i].position) {
            double ratio = (t - stops[i-1].position) / (stops[i].position - stops[i-1].position);
            *out_r = (uint8_t)(stops[i-1].r + (stops[i].r - stops[i-1].r) * ratio);
            *out_g = (uint8_t)(stops[i-1].g + (stops[i].g - stops[i-1].g) * ratio);
            *out_b = (uint8_t)(stops[i-1].b + (stops[i].b - stops[i-1].b) * ratio);
            return;
        }
    }

    *out_r = stops[num_stops - 1].r;
    *out_g = stops[num_stops - 1].g;
    *out_b = stops[num_stops - 1].b;
}

void generate_gradient(
    uint8_t* pixels, int width, int height,
    const ColorStop* stops, int num_stops,
    double angle, int mode // 0 = linear, 1 = conic, 2 = radial
) {
    double cos_angle = cos(angle * M_PI / 180.0);
    double sin_angle = sin(angle * M_PI / 180.0);

    double min_coord = 0.0, max_coord = 1.0;
    if (mode == 0) {
        double corners[4];
        corners[0] = 0 * cos_angle + 0 * sin_angle;
        corners[1] = (width - 1) * cos_angle + 0 * sin_angle;
        corners[2] = 0 * cos_angle + (height - 1) * sin_angle;
        corners[3] = (width - 1) * cos_angle + (height - 1) * sin_angle;

        min_coord = corners[0];
        max_coord = corners[0];
        for (int i = 1; i < 4; i++) {
            if (corners[i] < min_coord) min_coord = corners[i];
            if (corners[i] > max_coord) max_coord = corners[i];
        }
    }

    double range = max_coord - min_coord;
    if (range == 0) range = 1.0;

    double cx = width / 2.0;
    double cy = height / 2.0;
    double max_radius = sqrt(cx * cx + cy * cy);

    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            double t;

            if (mode == 0) { // Linear
                double coord = x * cos_angle + y * sin_angle;
                t = (coord - min_coord) / range;

            } else if (mode == 1) { // Conic
                double dx = x - cx;
                double dy = y - cy;
                t = (atan2(dy, dx) + M_PI) / (2 * M_PI);

            } else { // Radial
                double dx = x - cx;
                double dy = y - cy;
                double dist = sqrt(dx * dx + dy * dy);
                t = dist / max_radius;
            }

            if (t < 0) t = 0;
            if (t > 1) t = 1;

            uint8_t r, g, b;
            interpolate_color(t, stops, num_stops, &r, &g, &b);

            int idx = (y * width + x) * 4;
            pixels[idx] = r;
            pixels[idx + 1] = g;
            pixels[idx + 2] = b;
            pixels[idx + 3] = 255;
        }
    }
}

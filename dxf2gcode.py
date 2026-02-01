#!/usr/bin/env python3
"""Convert DXF files to G-code for laser cutting.

Supports LINE, CIRCLE, ARC, and LWPOLYLINE entities. Optionally prepends/appends
header and footer G-code files for machine startup and shutdown sequences.

Usage:
    dxf2gcode panel.dxf
    dxf2gcode panel.dxf -o panel.gcode -p 800 -f 3000
    dxf2gcode panel.dxf --header startup.gcode --footer shutdown.gcode
"""

import argparse
import math
import os
import sys

import ezdxf
from ezdxf.math import Vec2


class DXFToGcode:
    def __init__(self, power=1000, feed_rate=6000, rapid_rate=6000):
        self.power = power
        self.feed_rate = feed_rate
        self.rapid_rate = rapid_rate
        self.gcode = []
        self.current_pos = Vec2(0, 0)
        self.laser_on = False

    def add_header(self, header_file):
        """Add header G-code from file."""
        if os.path.exists(header_file):
            with open(header_file, "r") as f:
                self.gcode.append(f.read())
        else:
            print(f"Warning: header file not found: {header_file}", file=sys.stderr)

    def add_footer(self, footer_file):
        """Add footer G-code from file."""
        if os.path.exists(footer_file):
            with open(footer_file, "r") as f:
                self.gcode.append(f.read())
        else:
            print(f"Warning: footer file not found: {footer_file}", file=sys.stderr)

    def laser_off(self):
        if self.laser_on:
            self.gcode.append("M5")
            self.laser_on = False

    def laser_on_cmd(self):
        if not self.laser_on:
            self.gcode.append(f"M4 S{self.power}")
            self.laser_on = True

    def rapid_move(self, x, y):
        self.laser_off()
        self.gcode.append(f"G0 X{x:.3f} Y{y:.3f}")
        self.current_pos = Vec2(x, y)

    def linear_move(self, x, y):
        self.laser_on_cmd()
        self.gcode.append(f"G1 X{x:.3f} Y{y:.3f} F{self.feed_rate}")
        self.current_pos = Vec2(x, y)

    def arc_move(self, x, y, cx, cy, clockwise=True):
        self.laser_on_cmd()
        i = cx - self.current_pos.x
        j = cy - self.current_pos.y
        cmd = "G2" if clockwise else "G3"
        self.gcode.append(f"{cmd} X{x:.3f} Y{y:.3f} I{i:.3f} J{j:.3f} F{self.feed_rate}")
        self.current_pos = Vec2(x, y)

    def process_line(self, entity):
        start = Vec2(entity.dxf.start.x, entity.dxf.start.y)
        end = Vec2(entity.dxf.end.x, entity.dxf.end.y)
        if self.current_pos.distance(start) > 0.001:
            self.rapid_move(start.x, start.y)
        self.linear_move(end.x, end.y)

    def process_circle(self, entity):
        center = Vec2(entity.dxf.center.x, entity.dxf.center.y)
        radius = entity.dxf.radius
        start_x = center.x + radius
        start_y = center.y
        self.rapid_move(start_x, start_y)
        self.arc_move(center.x - radius, center.y, center.x, center.y, clockwise=True)
        self.arc_move(start_x, start_y, center.x, center.y, clockwise=True)

    def process_arc(self, entity):
        center = Vec2(entity.dxf.center.x, entity.dxf.center.y)
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)
        start_x = center.x + radius * math.cos(start_angle)
        start_y = center.y + radius * math.sin(start_angle)
        end_x = center.x + radius * math.cos(end_angle)
        end_y = center.y + radius * math.sin(end_angle)
        if self.current_pos.distance(Vec2(start_x, start_y)) > 0.001:
            self.rapid_move(start_x, start_y)
        self.arc_move(end_x, end_y, center.x, center.y, clockwise=False)

    def process_lwpolyline(self, entity):
        points = list(entity.points())
        if not points:
            return
        first = points[0]
        self.rapid_move(first[0], first[1])
        for i in range(len(points)):
            next_i = (i + 1) % len(points)
            if next_i == 0 and not entity.is_closed:
                break
            bulge = first[4] if i == 0 else points[i][4]
            next_point = points[next_i]
            if abs(bulge) < 0.001:
                self.linear_move(next_point[0], next_point[1])
            else:
                p1 = Vec2(points[i][0], points[i][1])
                p2 = Vec2(next_point[0], next_point[1])
                angle = 4 * math.atan(bulge)
                dist = p1.distance(p2)
                radius = dist / (2 * math.sin(angle / 2))
                mid = (p1 + p2) / 2
                h = radius * math.cos(angle / 2)
                perp = (p2 - p1).orthogonal(ccw=True).normalize()
                center = mid + perp * h
                self.arc_move(p2.x, p2.y, center.x, center.y, clockwise=(bulge < 0))

    def process_dxf(self, filename):
        """Process a DXF file and generate cutting G-code."""
        try:
            doc = ezdxf.readfile(filename)
        except Exception as e:
            print(f"Error reading DXF file: {e}", file=sys.stderr)
            return False

        msp = doc.modelspace()
        entity_count = 0

        for entity in msp:
            dtype = entity.dxftype()
            if dtype == "LINE":
                self.process_line(entity)
                entity_count += 1
            elif dtype == "CIRCLE":
                self.process_circle(entity)
                entity_count += 1
            elif dtype == "ARC":
                self.process_arc(entity)
                entity_count += 1
            elif dtype == "LWPOLYLINE":
                self.process_lwpolyline(entity)
                entity_count += 1

        self.laser_off()
        print(f"Processed {entity_count} entities")
        return True

    def save_gcode(self, filename):
        with open(filename, "w") as f:
            f.write("\n".join(self.gcode))


def main():
    parser = argparse.ArgumentParser(
        description="Convert DXF files to G-code for laser cutting",
        epilog="Example: dxf2gcode panel.dxf -o panel.gcode -p 800 -f 3000",
    )
    parser.add_argument("input", help="Input DXF file")
    parser.add_argument("-o", "--output", help="Output G-code file (default: <input>.gcode)")
    parser.add_argument("-p", "--power", type=int, default=1000, help="Laser power S value (default: 1000)")
    parser.add_argument("-f", "--feed", type=int, default=6000, help="Feed rate in mm/min (default: 6000)")
    parser.add_argument("-r", "--rapid", type=int, default=6000, help="Rapid rate in mm/min (default: 6000)")
    parser.add_argument("--no-header", action="store_true", help="Skip header file")
    parser.add_argument("--no-footer", action="store_true", help="Skip footer file")
    parser.add_argument("--header", help="Header G-code file (prepended before cutting)")
    parser.add_argument("--footer", help="Footer G-code file (appended after cutting)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    output = args.output or args.input.replace(".dxf", ".gcode")

    converter = DXFToGcode(power=args.power, feed_rate=args.feed, rapid_rate=args.rapid)

    if not args.no_header and args.header:
        converter.add_header(args.header)

    print(f"Converting {args.input}...")
    if not converter.process_dxf(args.input):
        return 1

    if not args.no_footer and args.footer:
        converter.add_footer(args.footer)

    converter.save_gcode(output)
    print(f"Saved to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

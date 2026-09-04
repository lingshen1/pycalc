import math
import os
import sys
import mmap
import struct
from rich.console import Console
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

MODES = ["Standard", "Scientific", "Programmer", "Graph"]

HELP_TEXTS = {
    "Standard": (
        "[bold cyan]Standard Mode Quick Help[/bold cyan]\n\n"
        "• [bold]Operators:[/bold] `+`, `-`, `*`, `/`, `**` (power), `//` (integer div), `%` (modulo)\n"
        "• [bold]Memory:[/bold] Type `ans` anywhere to use the previous result.\n"
        "• [bold]Commands:[/bold] `M` (Change Mode), `C` (Clear), `?` (Toggle Help), `Q` (Quit)"
    ),
    "Scientific": (
        "[bold cyan]Scientific Mode Quick Help[/bold cyan]\n\n"
        "• [bold]Functions:[/bold] `sin()`, `cos()`, `tan()`, `sqrt()`, `log()`, `log10()`, `factorial()`, etc.\n"
        "• [bold]Constants:[/bold] `pi`, `e`, `tau`\n"
        "• [bold]Memory & Cmds:[/bold] Use `ans`, switch modes with `M`, toggle help with `?`"
    ),
    "Programmer": (
        "[bold cyan]Programmer Mode Quick Help[/bold cyan]\n\n"
        "• [bold]Bitwise Ops:[/bold] `&` (AND), `|` (OR), `^` (XOR), `~` (NOT), `<<` (L-Shift), `>>` (R-Shift)\n"
        "• [bold]Base Inputs:[/bold] Hex (`0xFF`), Binary (`0b1010`), Octal (`0o77`)\n"
        "• [bold]Outputs:[/bold] Automatically displays DEC, HEX, OCT, and BIN breakdowns."
    ),
    "Graph": (
        "[bold cyan]Graph Mode Quick Help[/bold cyan]\n\n"
        "• [bold]Usage:[/bold] Type any mathematical expression containing variable `x`.\n"
        "• [bold]Examples:[/bold] `sin(x)`, `x**2 - 4`, `cos(x) * x`, `x**3 - 3*x`\n"
        "• [bold]Hardware:[/bold] Split-screen layout (Top text panel, bottom LCD area for graph via `/dev/fb0`)."
    )
}

def check_is_calculinux():
    """Detects if the current environment is CalcLinux via /etc/os-release."""
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                content = f.read().lower()
                if "calculinux" in content:
                    return True
    except Exception:
        pass
    return False

def rgb565(r, g, b):
    """Convert 8-bit RGB to 16-bit RGB565 packed bytes."""
    val = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    return struct.pack('<H', val)


class Calculator:
    def __init__(self):
        self.mode_idx = 0
        self.history = []
        self.ans = 0
        self.error = None
        self.showing_help = False
        self.last_plot_summary = None
        self.last_graph_expr = None
        self.is_calculinux = check_is_calculinux()
        if self.is_calculinux:
            self.clear_framebuffer()

    @property
    def mode(self):
        return MODES[self.mode_idx]

    def clear_framebuffer(self):
        """Clears the entire 320x320 framebuffer screen."""
        if self.is_calculinux:
            try:
                fb_path = "/dev/fb0"
                fb_size = 320 * 320 * 2
                with open(fb_path, "r+b") as f:
                    buf = mmap.mmap(f.fileno(), fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)
                    bg_pixel = rgb565(10, 10, 18)
                    buf[:] = bg_pixel * (320 * 320)
                    buf.flush()
            except Exception:
                pass

    def clear_graph_region(self):
        """Clears only the bottom graph portion (y: 130 to 319) on CalcLinux."""
        if self.is_calculinux:
            try:
                fb_path = "/dev/fb0"
                width = 320
                total_height = 320
                text_height = 130
                fb_size = width * total_height * 2
                with open(fb_path, "r+b") as f:
                    buf = mmap.mmap(f.fileno(), fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)
                    bg_pixel = rgb565(10, 10, 18)
                    for y in range(text_height, total_height):
                        start_idx = (y * width + 0) * 2
                        end_idx = (y * width + width) * 2
                        buf[start_idx:end_idx] = bg_pixel * width
                    buf.flush()
            except Exception:
                pass

    def get_namespace(self):
        ns = {
            "ans": self.ans,
            "abs": abs,
            "min": min,
            "max": max,
            "round": round,
            "int": int,
            "float": float
        }
        for name in dir(math):
            if not name.startswith("_"):
                ns[name] = getattr(math, name)
        if self.mode == "Programmer":
            ns.update({"hex": hex, "bin": bin, "oct": oct})
        return ns

    def draw_plot_to_fb(self, expr_str):
        """Renders the split-screen plot directly to /dev/fb0."""
        if not self.is_calculinux:
            return

        xmin, xmax = -10.0, 10.0
        width = 320
        total_height = 320
        text_height = 130
        graph_height = total_height - text_height
        graph_y_start = text_height

        xs = [xmin + i * (xmax - xmin) / (width - 1) for i in range(width)]
        ys = []
        ns_base = self.get_namespace()
        
        for x in xs:
            try:
                ns = ns_base.copy()
                ns['x'] = x
                y = eval(expr_str, {"__builtins__": {}}, ns)
                if isinstance(y, (int, float)) and math.isfinite(y):
                    ys.append(float(y))
                else:
                    ys.append(None)
            except Exception:
                ys.append(None)
                
        valid_ys = [y for y in ys if y is not None]
        if not valid_ys:
            self.error = "No valid Y values to plot for this expression."
            self.last_plot_summary = None
            return

        ymin, ymax = min(valid_ys), max(valid_ys)
        if ymin == ymax:
            ymin -= 1.0
            ymax += 1.0
        else:
            pad = (ymax - ymin) * 0.1
            ymin -= pad
            ymax += pad

        fb_path = "/dev/fb0"
        fb_size = width * total_height * 2
        try:
            with open(fb_path, "r+b") as f:
                buf = mmap.mmap(f.fileno(), fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)
                
                # Clear graph region
                bg_pixel = rgb565(10, 10, 18)
                for y in range(graph_y_start, total_height):
                    start_idx = (y * width + 0) * 2
                    end_idx = (y * width + width) * 2
                    buf[start_idx:end_idx] = bg_pixel * width
                
                def map_y(val):
                    if ymax == ymin:
                        return graph_y_start + graph_height // 2
                    norm = (val - ymin) / (ymax - ymin)
                    r = graph_y_start + int((1.0 - norm) * (graph_height - 1))
                    return max(graph_y_start, min(total_height - 1, r))

                # Draw axes
                axis_pixel = rgb565(70, 70, 90)
                if ymin <= 0 <= ymax:
                    zero_row = map_y(0)
                    for col in range(width):
                        idx = (zero_row * width + col) * 2
                        buf[idx:idx+2] = axis_pixel
                if xmin <= 0 <= xmax:
                    zero_col = int((0 - xmin) / (xmax - xmin) * (width - 1))
                    for row in range(graph_y_start, total_height):
                        idx = (row * width + zero_col) * 2
                        buf[idx:idx+2] = axis_pixel

                # Draw curve
                curve_pixel = rgb565(0, 255, 128)
                for px, y in enumerate(ys):
                    if y is not None:
                        py = map_y(y)
                        for offset in (-1, 0, 1):
                            target_y = py + offset
                            if graph_y_start <= target_y < total_height:
                                idx = (target_y * width + px) * 2
                                buf[idx:idx+2] = curve_pixel
                buf.flush()
            
            self.last_plot_summary = f"[green]Plotting: {expr_str}[/green] | [dim]Y: [{ymin:.2f}, {ymax:.2f}][/dim]"
            self.error = None
        except Exception:
            pass

    def generate_ascii_plot(self, expr_str):
        """Fallback ASCII text plot for non-CalcLinux."""
        xmin, xmax = -10.0, 10.0
        width, height = 55, 12
        xs = [xmin + i * (xmax - xmin) / (width - 1) for i in range(width)]
        ys = []
        ns_base = self.get_namespace()
        
        for x in xs:
            try:
                ns = ns_base.copy()
                ns['x'] = x
                y = eval(expr_str, {"__builtins__": {}}, ns)
                if isinstance(y, (int, float)) and math.isfinite(y):
                    ys.append(float(y))
                else:
                    ys.append(None)
            except Exception:
                ys.append(None)
                
        valid_ys = [y for y in ys if y is not None]
        if not valid_ys:
            self.error = "No valid Y values to plot for this expression."
            self.last_plot_summary = None
            return

        ymin, ymax = min(valid_ys), max(valid_ys)
        if ymin == ymax:
            ymin -= 1.0
            ymax += 1.0
        else:
            pad = (ymax - ymin) * 0.1
            ymin -= pad
            ymax += pad

        grid = [[' ' for _ in range(width)] for _ in range(height)]
        
        def y_to_row(y):
            if ymax == ymin:
                return height // 2
            r = int((ymax - y) / (ymax - ymin) * (height - 1))
            return max(0, min(height - 1, r))

        zero_col = int((0 - xmin) / (xmax - xmin) * (width - 1)) if xmin <= 0 <= xmax else None
        zero_row = y_to_row(0) if ymin <= 0 <= ymax else None

        for r in range(height):
            if zero_col is not None and 0 <= zero_col < width:
                grid[r][zero_col] = '│'
        if zero_row is not None and 0 <= zero_row < height:
            for c in range(width):
                if grid[zero_row][c] == '│':
                    grid[zero_row][c] = '┼'
                else:
                    grid[zero_row][c] = '─'

        for c, y in enumerate(ys):
            if y is not None:
                r = y_to_row(y)
                if 0 <= r < height and 0 <= c < width:
                    grid[r][c] = '●'

        plot_str = "\n".join("".join(row) for row in grid)
        self.last_plot_summary = f"{plot_str}\n[dim]Y: [{ymin:.2f}, {ymax:.2f}] | X: [{xmin}, {xmax}][/dim]"
        self.error = None

    def evaluate(self, expr):
        expr = expr.strip()
        if not expr:
            return
            
        cmd = expr.lower()
        if cmd in ['q', 'quit', 'exit']:
            sys.exit(0)
        elif cmd == '?':
            self.showing_help = not self.showing_help
            self.error = None
            return
        elif cmd in ['m', 'mode']:
            self.mode_idx = (self.mode_idx + 1) % len(MODES)
            self.error = None
            self.showing_help = False
            self.last_plot_summary = None
            self.last_graph_expr = None
            if self.mode != "Graph":
                self.clear_framebuffer()
            return
        elif cmd in ['c', 'clear']:
            self.history.clear()
            self.ans = 0
            self.error = None
            self.showing_help = False
            self.last_plot_summary = None
            self.last_graph_expr = None
            self.clear_framebuffer()
            return

        if self.showing_help:
            self.showing_help = False

        if self.mode == "Graph":
            self.last_graph_expr = expr
            if self.is_calculinux:
                self.draw_plot_to_fb(expr)
            else:
                self.generate_ascii_plot(expr)
        else:
            try:
                res = eval(expr, {"__builtins__": {}}, self.get_namespace())
                self.ans = res
                self.history.append((expr, res))
                if len(self.history) > 5:
                    self.history.pop(0)
                self.error = None
            except Exception as e:
                self.error = f"Invalid Expression: {e}"

    def render(self):
        console.clear()

        group_items = []

        if self.showing_help:
            help_content = HELP_TEXTS.get(self.mode, "No help available.")
            group_items.append(Text.from_markup(help_content))
        elif self.mode == "Graph":
            if self.last_plot_summary:
                group_items.append(Text.from_markup(self.last_plot_summary))
            else:
                group_items.append(Text("Type function of x to plot (e.g., sin(x), x**2 - 3)", style="dim italic"))
        else:
            table = Table(show_header=False, expand=True, box=None, padding=(0, 1))
            table.add_column(justify="right", style="dim cyan")
            table.add_column(justify="center", style="dim white", width=3)
            table.add_column(justify="left", style="bold green")

            for expr, res in self.history[:-1]:
                table.add_row(expr, "=", str(res))
            
            if self.history:
                last_expr, last_res = self.history[-1]
                table.add_row(
                    Text(last_expr, style="bold cyan"), 
                    Text("=", style="bold white"), 
                    Text(str(last_res), style="bold bright_green")
                )
            else:
                table.add_row(" ", " ", "0")
            
            group_items.append(table)

            if self.mode == "Programmer" and self.history:
                if isinstance(self.ans, int):
                    prog_info = (
                        f"\n[dim white]DEC:[/dim white] [cyan]{self.ans}[/cyan] | "
                        f"[dim white]HEX:[/dim white] [magenta]{hex(self.ans)}[/magenta] | "
                        f"[dim white]OCT:[/dim white] [yellow]{oct(self.ans)}[/yellow] | "
                        f"[dim white]BIN:[/dim white] [green]{bin(self.ans)}[/green]"
                    )
                    group_items.append(Text.from_markup(prog_info))

        if self.error:
            group_items.append(Text.from_markup(f"\n[bold red]✖ {self.error}[/bold red]"))
            
        sys_status = " [Split-Screen FB]" if self.is_calculinux and self.mode == "Graph" else ""
        header = f"[bold gold1] Calculator ⚡ {self.mode}{sys_status} [/bold gold1]"
        footer = "[dim]Commands: [bold]?[/bold] (Help) | [bold]M[/bold] (Mode) | [bold]C[/bold] (Clear) | [bold]Q[/bold] (Quit)[/dim]"
        
        panel = Panel(
            Group(*group_items),
            title=header,
            subtitle=footer,
            expand=False,
            border_style="blue"
        )
        console.print(panel)

        # Repaint framebuffer graph *after* console text redraws to override any fbcon clearing/refreshing
        if self.is_calculinux and self.mode == "Graph" and self.last_graph_expr:
            self.draw_plot_to_fb(self.last_graph_expr)


def main():
    calc = Calculator()
    while True:
        calc.render()
        try:
            expr = input("\n Enter expression or '?' ❯ ")
            calc.evaluate(expr)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Launch the Wuggy GUI.

Without --browser: opens a native app window via pywebview.
With --browser:    starts Flask and opens the default browser instead.
With --server:     starts Flask only (no window/browser), for CLI/remote use.
"""
import argparse
import socket
import threading

from wuggy.gui.app import app


def find_free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_flask(host, port, debug):
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wuggy GUI")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--browser", action="store_true",
                        help="Open in the default browser instead of a native window")
    parser.add_argument("--server", action="store_true",
                        help="Run Flask server only (no window or browser)")
    args = parser.parse_args()

    port = args.port or find_free_port()
    url = f"http://{args.host}:{port}"

    if args.server:
        print(f"Wuggy server running at {url}")
        app.run(host=args.host, port=port, debug=args.debug)

    elif args.browser:
        import webbrowser
        t = threading.Thread(target=start_flask, args=(args.host, port, args.debug), daemon=True)
        t.start()
        # Give Flask a moment to start before opening the browser
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        t.join()

    else:
        try:
            import webview
            from webview.menu import Menu, MenuAction
        except ImportError:
            import sys
            print("pywebview is not installed. Run with --browser to use the default browser instead.")
            sys.exit(1)

        t = threading.Thread(target=start_flask, args=(args.host, port, args.debug), daemon=True)
        t.start()

        def show_about():
            if webview.windows:
                webview.windows[0].evaluate_js("showAbout()")

        menu = [
            Menu("Help", [
                MenuAction("About Wuggy", show_about),
            ]),
        ]

        webview.create_window("Wuggy", url, width=1280, height=800, min_size=(800, 600))
        webview.start(menu=menu)

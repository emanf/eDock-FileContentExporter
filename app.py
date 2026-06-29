from core.app.app_base import AppBase

from .ui import ExporterWindow


class FileContentExporterApp(AppBase):
    def on_init(self):
        self.window = None

    def on_load(self):
        if self.window is None:
            self.window = ExporterWindow(app_ref=self)
            self.register_main_window(self.window)

    def on_unload(self):
        if self.window is not None:
            try:
                self.window.close()
            except Exception:
                pass
        self.window = None

    def run(self):
        if self.window is None:
            self.on_load()
        if self.window is not None:
            self.window.show_and_activate()


App = FileContentExporterApp

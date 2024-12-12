import FreeSimpleGUI as Sg

from cutom_popup import CustomActionPopup
from upload_files import DeviceDataUploader
from download_files import DeviceDataDownload


class App:
    def __init__(self, title, button_data, window_size=(400, 200)):
        """
        Initialize the window.

        :param title: Title of the window.
        :param button_data: List of tuples containing button labels and icon file paths.
                            Example: [("Button 1", "icon1.png"), ("Button 2", "icon2.png")]
        """
        self.title = title
        self.button_data = button_data
        self.window_size = window_size

        self.window = None

    def create_layout(self):
        """
        Create the layout for the window.
        """
        buttons = [
            Sg.Button(
                label,
                key=key, size=(20, 1),
                # image_filename=icon,
                # image_size=(32, 32),
                # image_subsample=3,
            )
            for label, key, icon in self.button_data
        ]
        return [buttons]

    def run(self):
        """
        Display the window and handle events.
        """
        layout = self.create_layout()
        self.window = Sg.Window(
            self.title, layout,
            size=self.window_size,  # Set window size
            element_justification="center"
        )

        while True:
            event, _ = self.window.read()
            if event == Sg.WINDOW_CLOSED:
                break
            elif event:
                print(event, _)
                self.on_button_click(event)

        self.window.close()

    def on_button_click(self, key):
        """
        Handle button click events.

        :param button_label: The label of the button that was clicked.
        """
        print(f"{key} clicked")

        if key == "upld":
            DeviceDataUploader().compile_lpc()
        elif key == "dwnld":
            print(f"{key} uploaded")
            DeviceDataDownload().compile_a7p()


if __name__ == "__main__":
    button_info = [("Download profiles", "dwnld", "download.png"), ("Upload profiles", "upld", "upload.png")]
    app = App("ArcherBC Resolver", button_info)
    app.run()

import FreeSimpleGUI as Sg
from a7p import A7PFile, A7PDataError
from a7p.protovalidate import ValidationError
from cutom_popup import CustomActionPopup


class SelectFiles:
    def __init__(self):
        self.files = []
        files = Sg.popup_get_file(
            "Select files",
            multiple_files=True,  # Allow multiple file selection
            file_types=(
                ("ArcherBC2", "*.a7p"),
            ),
            title="Open Files",
            no_window=True,  # Directly open the system file dialog without a PySimpleGUI window
        )
        if files:
            if len(files) > 20:
                Sg.popup("Too many files, device supports up to 20 profiles", title="Too many files", keep_on_top=True)
            else:
                self.files = files


class OpenFiles:
    def __init__(self, files):
        self.files = files

        self.data = []

        progress_layout = [
            [Sg.Text("Validating files", justification='center', key="counter")],
            [Sg.Text("", justification='center', key="filename", size=(30, 2))],
            [Sg.ProgressBar(max_value=len(self.files), orientation='h', size=(30, 20), key='PROGRESS')],
        ]
        progress_window = Sg.Window(
            "Validating files",
            progress_layout,
            modal=True,
            keep_on_top=True,
            finalize=True,
        )

        progress_bar = progress_window['PROGRESS']
        filename = progress_window['filename']
        counter = progress_window['counter']

        progress_bar.update(0)
        for i, file in enumerate(self.files):
            counter.update(f"Validating files: {i}/{len(self.files)}")
            filename.update(file)

            data, pop = self.open_file(file)

            if pop == "Abort":
                self.data = []
                break
            elif pop != "Skip" and data:
                if data:
                    self.data.append(data)

            progress_bar.update(i + 1)  # Update progress bar
            if progress_window.read(timeout=0)[0] == Sg.WINDOW_CLOSED:
                break  # Allow closing the popup manually

        print("Valid files count:", len(self.data))
        progress_window.close()

    @staticmethod
    def open_file(file):
        data, action = None, None

        try:
            with open(file, 'rb') as f:
                data = A7PFile.load(f, validate=True)
        except A7PDataError as e:
            action = CustomActionPopup(
                "Invalid file checksum, skip?",
                title="Invalid file checksum",
                actions=["Skip", "Abort"]
            ).open()
        except ValidationError as e:
            action = CustomActionPopup(
                "Invalid file data, skip?",
                title="Invalid file data",
                actions=["Skip", "Abort"]
            ).open()
        except IOError as e:
            action = CustomActionPopup(
                e,
                title="File open error",
                actions=["Skip", "Abort"]
            ).open()
        return data, action

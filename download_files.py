import FreeSimpleGUI as Sg
from rich.progress import Task
from archerdfu.dfus.archrw import ArcherRW
from archerdfu.factory.profiles import ProfileBuilder, Profile
from a7p.factory import A7PFactory

class Progress:
    def __init__(self, title="Progress"):
        self.title = title
        self.progress_layout = [
            [Sg.Text("Processing...", justification='center', key="counter")],
            [Sg.Text("", justification='center', key="filename", size=(30, 2))],
            [Sg.ProgressBar(max_value=100, orientation='h', size=(30, 20), key='PROGRESS')],
        ]
        self.progress_window = None

    def open(self):
        self.progress_window = Sg.Window(
            self.title,
            self.progress_layout,
            modal=True,
            keep_on_top=True,
            finalize=True,
        )

        self.update(100, 0, self.title)

    def close(self):
        self.progress_window.close()

    def update(self, total, completed, message):

        _value = round(100 * (completed / total))

        progress_bar = self.progress_window['PROGRESS']
        counter = self.progress_window['counter']

        progress_bar.update(0)
        counter.update(f"{message}: {_value}%")

        progress_bar.update(_value)  # Update progress bar
        # if progress_window.read(timeout=0)[0] == Sg.WINDOW_CLOSED:
        #     break  # Allow closing the popup manually

        if _value == total:
            self.close()


class DeviceDataDownload(ArcherRW):
    def __init__(self):
        super(DeviceDataDownload, self).__init__()

    def get_profiles(self):
        profiles, error = None, None
        params_progress = Progress("Downloading params...")
        profiles_progress = Progress("Downloading profiles...")

        def params_callback(task: Task):
            params_progress.update(task.total, task.completed, "Downloading params")

        def profiles_callback(task: Task):
            profiles_progress.update(task.total, task.completed, "Downloading params")

        try:
            params_progress.open()
            profiles_progress = Progress("Downloading params...")
            profiles_progress.open()
            params = self.read_device_params(callback=params_callback)
            profiles_buf = self.read_device_profiles(callback=profiles_callback)
            profiles = ProfileBuilder.parse(profiles_buf, params)
        except ConnectionError as err:
            error = err
            Sg.popup(
                "Can't connect to device",
                title="Error",
                keep_on_top=True
            )
        except IOError as err:
            error = err
            Sg.popup(
                "Error occurred while downloading device data",
                title="Downloading error",
                keep_on_top=True
            )
        except Exception as err:
            error = err
            Sg.popup(
                error,
                title="Downloading error",
                keep_on_top=True
            )
        finally:
            params_progress.close()
            profiles_progress.close()
            return profiles, error


p, err = DeviceDataDownload().get_profiles()


print(p[0])
print()

def create_a7p(profile: Profile):
    payload = A7PFactory(
        meta=A7PFactory.Meta(
            name=profile.get_name()
        )
    )


class CreateA7P:
    def __init__(self):
        ...


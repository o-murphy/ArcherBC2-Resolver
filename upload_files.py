import json

import FreeSimpleGUI as Sg
from a7p import A7PFile, A7PDataError
from a7p.protovalidate import ValidationError
from archerdfu.factory.profiles import ProfileBuilder, ProfilesPack
from rich.progress import Task

from cutom_popup import CustomActionPopup
from download_files import DeviceDataDownload, Progress


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


def a7p2lpc(payload):

    def get_bc_type(profile):
        print(profile.bc_type)
        if profile.bc_type == 0:
            return 1
        if profile.bc_type == 1:
            return 7
        if profile.bc_type == 2:
            return 9
        raise Exception("Unsupported drag model")

    profile = payload.profile
    return {
        "profile": {
            "weapon": {
                "name": profile.profile_name,
                "desc": profile.user_note,
                "cal_name": profile.caliber,
                "sight_height": profile.sc_height,
                "zero_dist": profile.distances[profile.c_zero_distance_idx] // 100,
                "twist": (profile.r_twist if profile.twist_dir == 0 else -profile.r_twist) / 100
            },
            "ammo": {
                "name": profile.cartridge_name,
                "desc": "",
                "v0": profile.c_muzzle_velocity // 10,
                "t0": profile.c_zero_temperature // 1,
                "powder_sens": profile.c_t_coeff / 1000
            },
            "bullet": {
                "name": profile.bullet_name,
                "drag_func": get_bc_type(profile),
                "bal_coeff": 0.3179999887943268,
                "diameter": 0.33799999952316284,
                "length": 1.5509999990463257,
                "weight": 250.0
            },
            "env": {
                "temperature": 29,
                "p_temperature": 29,
                "humidity": 33,
                "pressure": 753,
                "wind_speed": 0.0,
                "wind_angle": 270,
                "altitude": 0,
                "angle": 0,
                "azimuth": 270,
                "latitude": 75,
                "slope": 0
            }
        },
        "zeroing": {
            "x": -27.6705,
            "z": 0,
            "y": -58.533750000000005
        },
        "drag_func": None,
        "distances": list(range(100, 1700, 100))
    }


def compile_lpc():
    files = SelectFiles().files
    if not files:
        return

    datas = OpenFiles(files).data
    if not datas:
        return

    # if CustomActionPopup(
    #         "Are you sure to write data to the device?\nAfter pressing ok you can't undo this action",
    #         title="ALERT!",
    #         actions=['Cancel', 'Submit']
    # ).open() != 'Submit':
    #     return

    json_image = {
        "header": {
            "c_sight_data": {
                "sight_name": "ARCHER DEVICE",
                "clicks": {
                    "pClickX": 1419,
                    "pClickY": 1419
                }
            },
            "c_envir": {
                "temperature": 0,
                "p_temperature": 0,
                "humidity": 0,
                "pressure": 0,
                "wind_speed": 0.0,
                "wind_angle": 0,
                "altitude": 0,
                "angle": 0,
                "azimuth": 0,
                "latitude": 0,
                "slope": 0
            }
        },
        "profiles": [
            a7p2lpc(payload) for payload in datas
        ]
    }

    profiles_progress = Progress("Uploading profiles...")

    def profiles_callback(task: Task):
        profiles_progress.update(task.total, task.completed, "Uploading profiles")

    try:
        dev = DeviceDataDownload().find()
        image = ProfilesPack(**json_image)
        image.sort()
        profiles_progress.open()
        load_status = ProfileBuilder.write_to_dev(dev, image, callback=profiles_callback)

        if isinstance(load_status, int):
            if load_status >= 0:
                print("Uploading success")
                return
        raise IOError('Uploading failed')
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
    # except Exception as err:
    #     error = err
    #     Sg.popup(
    #         error,
    #         title="Downloading error",
    #         keep_on_top=True
    #     )
    finally:
        profiles_progress.close()


if __name__ == "__main__":
    compile_lpc()

import os.path
import re
from datetime import datetime

import FreeSimpleGUI as Sg
from a7p import A7PFile
from a7p.factory import A7PFactory
from a7p.protovalidate import ValidationError
from archerdfu.dfus.archrw import ArcherRW
from archerdfu.factory.caliber_icon import CaliberIcon
from archerdfu.factory.profiles import ProfileBuilder, BallisticProfile
from rich.progress import Task



DEFAULT_APP_DIR = os.path.join(os.path.expanduser("~"), "ArcherBC2-Resolver")

os.makedirs(DEFAULT_APP_DIR, exist_ok=True)

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


class SelectDirectory:
    def __init__(self):
        self.directory = ""
        # Open a directory selection dialog
        directory = Sg.popup_get_folder(
            "Select a directory to save files",
            title="Select Directory",
            no_window=True,  # Directly open the system folder dialog
            initial_folder=DEFAULT_APP_DIR
        )
        if directory:
            self.directory = directory
        else:
            Sg.popup("No directory selected", title="No Selection", keep_on_top=True)


class DeviceDataDownload(ArcherRW):
    def __init__(self):
        super(DeviceDataDownload, self).__init__()

    def get_profiles(self):
        profiles, info, error = None, None, None
        info_progress = Progress("Downloading info...")
        profiles_progress = Progress("Downloading profiles...")

        def info_callback(task: Task):
            info_progress.update(task.total, task.completed, "Downloading info")

        def profiles_callback(task: Task):
            profiles_progress.update(task.total, task.completed, "Downloading profiles")

        try:
            info_progress.open()
            info = self.read_device_info(callback=info_callback)
            profiles_progress.open()
            profiles = ProfileBuilder.read_from_dev(self, callback=profiles_callback)
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
            info_progress.close()
            profiles_progress.close()
            return profiles, info, error

    def get_reticles(self):
        reticles, error = None, None
        reticles_progress = Progress("Downloading reticles...")

        def reticles_callback(task: Task):
            reticles_progress.update(task.total, task.completed, "Downloading info")

        try:
            reticles_progress.open()
            reticles = self.read_device_reticles(callback=reticles_callback)
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
            reticles_progress.close()
            return reticles, error


    def compile_a7p(self):

        profiles, info, err = self.get_profiles()
        if err:
            return

        directory = SelectDirectory().directory
        if not directory:
            Sg.popup("Please select directory where to download the files", title="No directory", keep_on_top=True)
            return

        clicks = profiles.header.c_sight_data.clicks
        now_date = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        directory = os.path.join(
            directory,
            f"{sanitize_filename(info.serial_number_device)}_{now_date}"
        )
        os.makedirs(directory, exist_ok=True)

        decompiling_progress = Progress("Decompiling profiles...")
        decompiling_progress.open()
        try:
            for i, p in enumerate(profiles):
                decompiling_progress.update(len(profiles), i, "Decompiling profiles")
                try:
                    payload = create_a7p(p, clicks, info.serial_number_device)

                    filename = sanitize_filename(
                        f"{i}_{payload.profile.profile_name}_{payload.profile.bullet_name}_{now_date}_prof.a7p"
                    )
                    filename = os.path.join(directory, filename)
                    with open(filename, 'wb') as fp:
                        A7PFile.dump(payload, fp, validate=True)
                except ValidationError as err:
                    Sg.popup(f"Error in profile: {i}")
                except Exception as err:
                    Sg.popup(f"Error in profile: {i}")
        finally:
            decompiling_progress.close()


def sanitize_filename(name: str) -> str:
    """
    Removes or replaces unsupported characters in a file name.
    Allowed characters are alphanumeric, underscores, and dashes.
    """
    # Replace unsupported characters with underscores
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def stringify_float(value: float) -> str:
    """
    Converts a float to a string.
    If the value has no fractional part after rounding to one decimal place,
    the decimal point is omitted.
    """
    rounded_value = round(value, 1)
    if rounded_value.is_integer():
        return str(int(rounded_value))
    return f"{rounded_value}"


def get_drag_type(value):
    if value == 7:
        return "G7"
    if value == 1:
        return "G1",
    return "CUSTOM"


def get_coef_rows(profile, drag):
    if profile.bullet.drag_func == 7 or profile.bullet.drag_func == 1:
        return (A7PFactory.DragPoint(profile.bullet.bal_coeff, 0.),)
    if drag:
        output_drag = []
        for container in drag:
            mach, cd = container.mach, container.cd
            output_drag.append(
                A7PFactory.DragPoint(
                    coeff=cd,
                    velocity=mach
                )
            )
        return tuple(output_drag)
    raise Exception("Error on loading drag model")


def round_to_quarter(value):
    return round(value * 4) / 4


def create_a7p(bprofile: BallisticProfile, clicks, serial_num: str):
    profile, drag = bprofile.profile
    zeroing = bprofile.zeroing

    distances = tuple(sorted(
        d for d in (profile.weapon.zero_dist, *bprofile.distances) if d > 0
    ))

    payload = A7PFactory(
        meta=A7PFactory.Meta(
            name=profile.weapon.name,
            short_name_top=CaliberIcon.trunc_caliber(profile.weapon.cal_name),
            short_name_bot=f"{stringify_float(profile.bullet.weight)}gr",
            user_note=f"{profile.weapon.desc}"
        ),
        barrel=A7PFactory.Barrel(
            caliber=profile.weapon.cal_name,
            sight_height=profile.weapon.sight_height,
            twist=abs(profile.weapon.twist),
            twist_dir="RIGHT" if profile.weapon.twist >= 0 else "LEFT",
        ),
        cartridge=A7PFactory.Cartridge(
            name=profile.ammo.name,
            muzzle_velocity=profile.ammo.v0,
            temperature=profile.ammo.t0,
            powder_sens=profile.ammo.powder_sens,
        ),
        bullet=A7PFactory.Bullet(
            name=profile.bullet.name,
            diameter=profile.bullet.diameter,
            weight=profile.bullet.weight,
            length=profile.bullet.length,
            drag_type=get_drag_type(profile.bullet.drag_func),
            drag_model=get_coef_rows(profile, drag),
        ),
        zeroing=A7PFactory.Zeroing(
            x=round_to_quarter(zeroing.x / (clicks.pClickX / 1000)),
            y=round_to_quarter(zeroing.y / (clicks.pClickY / 1000)),
            pitch=profile.env.angle,
            distance=profile.weapon.zero_dist,
        ),
        zero_atmo=A7PFactory.Atmosphere(
            temperature=profile.env.temperature,
            pressure=round(profile.env.pressure * 1.33322),
            humidity=profile.env.humidity
        ),
        zero_powder_temp=profile.env.p_temperature,
        distances=distances,
        # switches  # using defaults
    )

    uuid = "00000000-0000-0000-0000-000000000000"
    uuid = uuid[:-len(serial_num)] + serial_num

    payload.profile.device_uuid = uuid  # temporary
    return payload


if __name__ == '__main__':
    DeviceDataDownload().compile_a7p()

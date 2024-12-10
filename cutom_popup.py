import FreeSimpleGUI as Sg


class ErrorPopup:
    def __init__(self, message, title = "Error"):
        self.message = message
        self.title = title

    def open(self):
        """
        Display a popup with custom actions.

        :param message: Message to display in the popup.
        :param title: Title of the popup window.
        :param actions: List of action button labels.
        :return: The label of the button that was clicked.
        """
        layout = [
            [Sg.Text("ERROR!")],
            [Sg.Text(self.message)],
            [Sg.Button("Close", button_color="red", key="close")]
        ]

        window = Sg.Window(
            self.title,
            layout,
            modal=True,
            keep_on_top=True,
        )

        while True:
            event, _ = window.read()
            if event == Sg.WINDOW_CLOSED:
                result = None  # No action was chosen
                break
            else:
                result = event  # Return the label of the button clicked
                break

        window.close()
        return result



class CustomActionPopup:
    def __init__(self, message, title, actions):
        self.message = message
        self.title = title
        self.actions = actions

    def open(self):
        """
        Display a popup with custom actions.

        :param message: Message to display in the popup.
        :param title: Title of the popup window.
        :param actions: List of action button labels.
        :return: The label of the button that was clicked.
        """
        layout = [
            [Sg.Text(self.message)],
            [Sg.Button(action, key=action) for action in self.actions],
        ]

        window = Sg.Window(self.title, layout, modal=True, keep_on_top=True)

        while True:
            event, _ = window.read()
            if event == Sg.WINDOW_CLOSED:
                result = None  # No action was chosen
                break
            else:
                result = event  # Return the label of the button clicked
                break

        window.close()
        return result

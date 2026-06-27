import logging

from panels.menu import Panel as MenuPanel


class Panel(MenuPanel):
    def __init__(self, screen, title, items=None):
        super().__init__(screen, title, items)
        logging.info("### Making CNC MainMenu")

    def add_content(self):
        for child in self.scroll.get_children():
            self.scroll.remove(child)
        columns = 3 if self._screen.vertical_mode else 4
        self.scroll.add(self.arrangeMenuItems(self.items, columns, True))
        if not self.content.get_children():
            self.content.add(self.scroll)

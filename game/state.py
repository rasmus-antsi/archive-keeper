"""What the player has done so far. One object, reset when a new game starts."""


class GameState:
    def __init__(self, content):
        self.total = len(content.documents)
        self.solved = set()        # ids of documents whose memory is restored
        self.seen = set()          # one-off moments already shown, by name
        self.archive_pos = None    # where the ghost stood when it left the archive room
        self.shelf_cursor = {}     # shelf id -> last selected entry

    @property
    def all_solved(self):
        return len(self.solved) >= self.total

    def first_time(self, name):
        """True the first time it is asked about a name, False ever after."""
        if name in self.seen:
            return False
        self.seen.add(name)
        return True

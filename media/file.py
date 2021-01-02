import os
import re
import hashlib
import mutagen

import util
import variables as var
from media.item import BaseItem, item_builders, item_loaders, item_id_generators, ValidationFailedError
from constants import tr_cli as tr

'''
type : file
    id
    path
    title
    artist
    duration
    user
'''


def file_item_builder(**kwargs):
    return FileItem(kwargs['path'])


def file_item_loader(_dict):
    return FileItem("", _dict)


def file_item_id_generator(**kwargs):
    return hashlib.md5(kwargs['path'].encode()).hexdigest()


item_builders['file'] = file_item_builder
item_loaders['file'] = file_item_loader
item_id_generators['file'] = file_item_id_generator


class FileItem(BaseItem):
    def __init__(self, path, from_dict=None):
        if not from_dict:
            super().__init__()
            self.path = path
            self.title = ""
            self.artist = ""
            self.album = ""
            self.id = hashlib.md5(path.encode()).hexdigest()
            if os.path.exists(self.uri()):
                self._get_info_from_tag()
                self.ready = "yes"
                self.duration = util.get_media_duration(self.uri())
            self.keywords = self.title + " " + self.artist
        else:
            super().__init__(from_dict)
            self.artist = from_dict['artist']
            try:
                self.validate()
            except ValidationFailedError:
                self.ready = "failed"

        self.type = "file"

    def uri(self):
        return var.music_folder + self.path if self.path[0] != "/" else self.path

    def is_ready(self):
        return True

    def validate(self):
        if not os.path.exists(self.uri()):
            self.log.info(
                "file: music file missed for %s" % self.format_debug_string())
            raise ValidationFailedError(tr('file_missed', file=self.path))

        if self.duration == 0:
            self.duration = util.get_media_duration(self.uri())
            self.version += 1  # 0 -> 1, notify the wrapper to save me
        self.ready = "yes"
        return True

    def _get_info_from_tag(self):
        match = re.search(r"(.+)\.(.+)", self.uri())
        assert match is not None

        file_no_ext = match[1]
        ext = match[2]

        try:
            if ext == "mp3":
                # title: TIT2
                # artist: TPE1, TPE2
                # album: TALB
                # cover artwork: APIC:
                tags = mutagen.File(self.uri())
                if 'TIT2' in tags:
                    self.title = tags['TIT2'].text[0]
                if 'TPE1' in tags:  # artist
                    self.artist = tags['TPE1'].text[0]

            elif ext == "m4a" or ext == "m4b" or ext == "mp4" or ext == "m4p":
                # title: ©nam (\xa9nam)
                # artist: ©ART
                # album: ©alb
                # cover artwork: covr
                tags = mutagen.File(self.uri())
                if '©nam' in tags:
                    self.title = tags['©nam'][0]
                if '©ART' in tags:  # artist
                    self.artist = tags['©ART'][0]

            elif ext == "opus":
                # title: 'title'
                # artist: 'artist'
                # album: 'album'
                tags = mutagen.File(self.uri())
                if 'title' in tags:
                    self.title = tags['title'][0]
                if 'artist' in tags:
                    self.artist = tags['artist'][0]
                if 'album' in tags:
                    self.album = tags['album'][0]

        except:
            pass

        if not self.title:
            self.title = os.path.basename(file_no_ext)

    def to_dict(self):
        dict = super().to_dict()
        dict['type'] = 'file'
        dict['path'] = self.path
        dict['title'] = self.title
        dict['artist'] = self.artist
        dict['album'] = self.album
        return dict

    def format_debug_string(self):
        return "[file] {descrip} ({path})".format(
            descrip=self.format_title(),
            path=self.path
        )

    def format_song_string(self, user):
        return tr("file_item",
                  title=self.title,
                  artist=self.artist if self.artist else '??',
                  user=user
                  )

    def format_current_playing(self, user):
        display = tr("now_playing", item=self.format_song_string(user))

        return display

    def format_title(self):
        title = self.title if self.title else self.path
        if self.artist:
            return self.artist + " - " + title
        else:
            return title

    def display_type(self):
        return tr("file")

import os
import re

import googleapiclient.discovery
import googleapiclient.errors

from secrets import YOUTUBE_API_KEY

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

zeos_channel_id = "UC3XdYJjWliOdKuZMNaTiP8Q"
zeos_second_channel_id = "UCOtI5JChjkQVYRWAbqRhNeQ"

hyphen_line_regex = r"^[- ?]+$"
bad_time_regex = r"[\d]{1,2}:[\d]{1,2} - [\d]{1,2}:[\d]{1,2} - [\d]{1,2}:[\d]{1,2}"
time_stamp_regex = r"(?:[\d]{1,2}:?){3} "
only_symbols_and_numbers_regex = r"^[^A-Za-z]+$"
songs_identifiers = ["song list", "songs list", "s o n g l i s t", "sound demo"]
exclusions = [
    "intro",
    "leak test",
    "lack of leak test",
    "final words",
    "creepy fingers",
    "- intro",
    "final thought",
    "final thoughts",
    "thanks to delta deka for timestamps",
    "final word",
]


def main():
    descriptions = all_descriptions()

    # write_descriptions(descriptions)

    songs = []
    for description in descriptions:
        songs.extend(extract_songs_from_description(description))

    filtered_songs = filter_songs(songs)

    with open("songs.txt", "w") as f:
        f.write("\n".join(filtered_songs))


def write_descriptions(descriptions):
    for index, description in enumerate(descriptions):
        num_pieces = len(re.split(hyphen_line_regex, description, flags=re.MULTILINE))
        is_good = any(
            [identifier in description.lower() for identifier in songs_identifiers]
        )
        file_path = (
            f"descriptions/{'good' if is_good else 'bad'}/{num_pieces}/{index}.txt"
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(description)


def descriptions_by_channel_id(youtube, channel_id):
    playlist_id = uploads_playlist_id(youtube, channel_id)
    return video_descriptions(youtube, playlist_id)


def uploads_playlist_id(youtube, channel_id):
    request = youtube.channels().list(part="contentDetails", id=channel_id)
    response = request.execute()
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def video_descriptions(youtube, playlist_id):
    descriptions = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            maxResults=50,
            pageToken=next_page_token,
            playlistId=playlist_id,
        )
        response = request.execute()

        descriptions.extend(
            [
                item["snippet"]["description"]
                for item in response["items"]
                if "[SOUND DEMO]" in item["snippet"]["title"]
            ]
        )

        if "nextPageToken" not in response:
            break

        next_page_token = response["nextPageToken"]

    return descriptions


def all_descriptions():
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"

    # Get credentials and create an API client
    youtube = googleapiclient.discovery.build(
        api_service_name,
        api_version,
        developerKey=YOUTUBE_API_KEY,
    )

    descriptions = []
    descriptions.extend(descriptions_by_channel_id(youtube, zeos_channel_id))
    descriptions.extend(descriptions_by_channel_id(youtube, zeos_second_channel_id))

    return descriptions


def extract_songs_from_description(description):
    split_description = re.split(hyphen_line_regex, description, flags=re.MULTILINE)
    if is_songs_identifier_in_string(description):
        return extract_songs_after_identifier(description)
    elif len(split_description) == 6:
        return extract_songs_from_split(split_description)
    else:
        return extract_songs_with_regex(description)


def filter_songs(songs):
    # This is better, but I want to see everything ordered for now
    # filtered_songs = set()
    filtered_songs = []

    for song in songs:
        song = song.strip()
        if re.search(time_stamp_regex, song):
            song = re.sub(time_stamp_regex, "", song)

        if should_keep(song, filtered_songs):
            filtered_songs.append(song)

    return filtered_songs


def should_keep(song, songs):
    exists = song != ""
    has_bad_time_regex = re.match(bad_time_regex, song)
    is_only_symbols_and_numbers = re.match(only_symbols_and_numbers_regex, song)
    excludable = song.lower() in exclusions
    contains_url = "http" in song
    already_recorded = song in songs

    return (
        exists
        and not has_bad_time_regex
        and not is_only_symbols_and_numbers
        and not excludable
        and not contains_url
        and not already_recorded
    )


def extract_songs_after_identifier(description):
    songs = []
    is_after_identifier = False
    for line in description.splitlines():
        if is_songs_identifier_in_string(line):
            is_after_identifier = True
            continue

        if is_after_identifier and line:
            songs.append(line)
        elif is_after_identifier and (not line or re.match(hyphen_line_regex, line)):
            break

    return songs


def extract_songs_from_split(split_description):
    songs = []

    for line in split_description[2].splitlines():
        songs.append(line)

    return songs


def extract_songs_with_regex(description):
    regex = r"^(?:[a-zA-Z0-9 '&.()!,]+ - )+[a-zA-Z0-9 '&.()!,]+$"
    return re.findall(regex, description, flags=re.MULTILINE)


def is_songs_identifier_in_string(string):
    return any([identifier in string.lower() for identifier in songs_identifiers])


if __name__ == "__main__":
    main()

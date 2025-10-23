import os
import subprocess

def format_srt_timestamp(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def parse_srt(transcripts: list[dict]) -> str:
    """Convert a list of transcript dictionaries to SRT format."""
    srt_content = ""
    for idx, item in enumerate(transcripts, start=1):
        start_time = format_srt_timestamp(item['dt_start'])
        end_time = format_srt_timestamp(item['dt_end'])
        content = item['content'].replace('\n', ' ').strip()
        srt_content += f"{idx}\n{start_time} --> {end_time}\n{content}\n\n"
    return srt_content.strip()

def save_srt(transcripts: list[dict], filepath: os.PathLike):
    """Save transcripts to an SRT file."""
    srt_content = parse_srt(transcripts)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(srt_content)

def aria2(dir_path: os.PathLike):
    """Use aria2 to download files listed in download.txt within `dir_path`."""
    command = [
        'aria2c',
        '-x', '16',
        '-s', '16',
        '-k', '1M',
        '--auto-file-renaming=false',
        '--allow-overwrite=false',
        '--conditional-get=true',
        '-d', dir_path,
        '-i', f"{dir_path}/download.txt"
    ]
    subprocess.run(command)
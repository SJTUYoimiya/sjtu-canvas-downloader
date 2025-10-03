import subprocess
import os.path

def download_video(dir_path: os.PathLike):
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

def download(courses: list[dict], download_dir: str, classroom_only: bool = False):
    os.makedirs(download_dir, exist_ok=True)
    
    download_queue = []
    for course in courses:
        course_name = course.get('name')
        for k, v in course.get('download_urls', {}).items():
            if classroom_only and int(k) == 1:
                continue

            exf = v.split('?')[0].split('.')[-1]
            output_path = f"{course_name}_{k}.{exf}"
            
            download_queue.append((v, output_path))

    download_txt = ''.join([f"{url}\n  out={path}\n" for url, path in download_queue])
    with open(os.path.join(download_dir, 'download.txt'), 'w') as f:
        f.write(download_txt)

    download_video(download_dir)

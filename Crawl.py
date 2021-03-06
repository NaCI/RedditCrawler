import os
import errno
from enum import Enum
import urllib
import requests
from bs4 import BeautifulSoup
import json
import shutil
from random import randrange
import sys
import argparse

is_test_mode = True  # //TODO : change test mode to False when development ends
base_url = r'https://www.reddit.com/r/DotA2/'  # url for crawling
base_top_url = r'https://www.reddit.com'
folder_name = 'Reddit_Dota'  # Directory name on desktop assigned to save data from reddit
preferred_video_quality = ['720', '720p']


class DataDomain(Enum):
    Twitch = "clips.twitch.tv"
    Gfycat = "gfycat.com"
    Youtube = "youtube.com"
    Ireddit = "i.redd.it"
    Streamable = "streamable.com"
    Imgur = "imgur.com"  # // TODO : imgur için proxy üzerinden bir bağlantı kodu yaz
    Self = "self.DotA2"
    Twitter = "twitter.com"


videoDomains = [DataDomain.Twitch.value, DataDomain.Gfycat.value, DataDomain.Youtube.value, DataDomain.Streamable.value]
imgDomains = [DataDomain.Ireddit.value]
user_agent = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
headers = {
        'User-Agent': user_agent,
    }


# Generate Help file for command line usage
parser = argparse.ArgumentParser(
    description='''This script gets data from "reddit.com/r/Dota2" and download videos/images if requested''',
    usage='Crawl.py 3 True',
    epilog="""Download directory path : ~/Desktop/Reddit_Dota """)
parser.add_argument('max_page', nargs='?', type=int, default=3,
                    help='Max page number to be parsed! (Default value is : 3)')
parser.add_argument('download', nargs='?', type=str, default='True', choices=['True', 'False'],
                    help='Download videos and images if requested! (Default value is : True)')
args = parser.parse_args()


def print_test(*args, **kwargs):
    if is_test_mode:
        print(*args, **kwargs)


def str_to_bool(s):
    if s == 'True':
        return True
    elif s == 'False':
        return False
    else:
        raise ValueError("Cannot covert {} to a bool".format(s))


def create_folder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def get_desktop_location():
    # get desktop location
    return os.path.join(os.environ['HOMEPATH'], "Desktop")


def get_redirect_url(url, need_decode=False):
    if need_decode:
        url = urllib.parse.unquote(url)
    r = requests.get(url, headers=headers)
    print_test("Get Redirect Url - url : {}".format(r.url))
    return r.url


def download_web_file(url, directory):
    print_test("Download Web File - Url : {} - Directory : {}".format(url, directory))
    if url:
        urllib.request.urlretrieve(url, directory)


def download_web_file_with_header(url, directory):
    print_test("Download Web File With Header - Url : {} - Directory : {}".format(url, directory))
    # set user agent
    # urllib.request.urlopen.version = user_agent
    req = urllib.request.Request(
        url,
        data=None,
        headers=headers
    )
    resp = urllib.request.urlopen(req)
    with resp, open(directory, 'wb') as out_file:
        shutil.copyfileobj(resp, out_file)


def get_reddit_dota_folder_directory():
    folder_directory = os.path.join(get_desktop_location(), folder_name)
    return folder_directory


def add_filename_extension(data_domain, filename):
    if data_domain in videoDomains:
        filename += ".mp4"
    if data_domain in imgDomains:
        filename += ".png"
    return filename


video_quality_keyword = "quality"
video_source_keyword = "source"


def get_video_url_from_twitch(url):
    clip_info_keyword = "clipInfo"
    quality_options_keyword = "quality_options"
    video_links = []
    video_url = None
    try:
        source_code_text = requests.get(url, headers=headers).text
        if source_code_text:
            soup_twitch = BeautifulSoup(source_code_text, "html.parser")
            last_script_tag = soup_twitch.find_all('script')[-1].string
            clip_info = last_script_tag[last_script_tag.index(clip_info_keyword):]
            clip_info = '{%s}' % (clip_info.split('{', 1)[1].rsplit('};', 1)[0],)
            # print_test(clip_info)
            quality_options = clip_info[clip_info.index(quality_options_keyword):]
            quality_options = '[%s]' % (quality_options.split('[', 1)[1].split('],', 1)[0],)
            # print_test("Quality Options Raw Data : {}\n\n".format(quality_options))
            json_data = json.loads(quality_options)
            # print_test(json_data)
            for json_object in json_data:
                video_quality = json_object[video_quality_keyword]
                video_source = json_object[video_source_keyword]
                if str(video_quality) in preferred_video_quality:
                    video_url = video_source
                    break
                video_links.append({video_quality_keyword: video_quality, video_source_keyword: video_source})
            # print_test(video_links)
            if not video_url:
                video_url = video_links[0][video_source_keyword]
            return video_url
    except BaseException as e:
        print("Error occured on getting video data from Twitch")
        raise


def get_video_url_from_gfycat(url):
    video_url = None
    try:
        source_code_text = requests.get(url, headers=headers).text
        if source_code_text:
            soup_gfycat = BeautifulSoup(source_code_text, "html.parser")
            video_url = soup_gfycat.find_all('source', {'type': 'video/mp4'})[-1].get('src')
        return video_url
    except BaseException as e:
        print("Error occured on getting video data from Gfycat")
        raise


def get_video_url_from_youtube(url):
    youtube_watch_keyword = "watch?"
    weibomiaopai_url = "https://weibomiaopai.com/online-video-downloader/youtube"
    weibomiaopai_serverlist = ['helloacm.com', 'happyukgo.com', 'uploadbeta.com', 'steakovercooked.com']
    weibomiaopai_hash_keyword = "var hash ="
    video_url = None
    hash_value = None
    if youtube_watch_keyword not in url:
        return video_url
    try:
        # get hash value from weibomiaopai
        source_weibomiaopai_text = requests.get(weibomiaopai_url, headers=headers).text
        if source_weibomiaopai_text:
            soup_weibomiaopai = BeautifulSoup(source_weibomiaopai_text, "html.parser")
            for script_tag in soup_weibomiaopai.find_all('script', {'type': 'text/rocketscript'}):
                if weibomiaopai_hash_keyword in script_tag.text:
                    hash_value = script_tag.text[script_tag.text.find(weibomiaopai_hash_keyword) + len(weibomiaopai_hash_keyword):]
                    hash_value = hash_value[: hash_value.find(';')]
                    hash_value = hash_value.strip().replace('"', '')
                    print_test("Hash Value : {}".format(hash_value))
                    break
            if not hash_value:
                print("Get Video Url From Youtube : Hash Value couldn't find")
                return None
            selected_server = weibomiaopai_serverlist[randrange(0, len(weibomiaopai_serverlist))]
            youtube_video_data_request = "https://" + selected_server + \
                                         "/api/video/?cached&lang=en&page=youtube&hash=" + hash_value + \
                                         "&video="+urllib.parse.quote_plus(url)
            source_youtube_video_data = requests.get(youtube_video_data_request, headers=headers).text
            print_test(source_youtube_video_data)
            json_youtube = json.loads(source_youtube_video_data)
            youtube_raw_url = str(json_youtube['url'])
            print_test("Youtube Raw Url : {}".format(youtube_raw_url))
            video_url = get_redirect_url(youtube_raw_url, True)
        return video_url
    except BaseException as e:
        print("Error occured on getting video data from Youtube")
        raise


def get_video_url_from_streamable(url):
    video_url = None
    try:
        source_code_text = requests.get(url, headers=headers).text
        if source_code_text:
            soup_stremable = BeautifulSoup(source_code_text, "html.parser")
            video_url = soup_stremable.find_all('source', {'type': 'video/mp4'})[0].get('src')
        return video_url
    except BaseException as e:
        print("Error occured on getting video data from Gfycat")
        raise


def save_to_folder(data_domain, data_url, title, category):
    print_test("Save To Folder - data_domain : {} - data_url : {} - title : {} - category : {}".
               format(data_domain, data_url, title, category))
    folder_directory = get_reddit_dota_folder_directory()
    create_folder(folder_directory)
    if category:
        title = category + " - " + title
    # < > | / \ : * ? " bad characters for folders
    title = title.replace(r'<', '').replace(r'>', '').replace(r'|', '').replace(r'/', '').replace('\\', '')\
        .replace(r':', '').replace(r'*', '').replace(r'?', '').replace(r'"', '')
    data_directory = os.path.join(folder_directory, title)
    data_directory = add_filename_extension(data_domain, data_directory)
    if os.path.isfile(data_directory):
        print("Save to folder - File already exist - File_name : {}".format(data_directory))
        return
    if data_domain == DataDomain.Twitch.value:
        video_url = get_video_url_from_twitch(data_url)
        # print_test("Save To Folder - Twitch - Video Url : {}".format(video_url))
        download_web_file(video_url, data_directory)
    elif data_domain == DataDomain.Ireddit.value:
        download_web_file(data_url, data_directory)
    elif data_domain == DataDomain.Gfycat.value:
        video_url = get_video_url_from_gfycat(data_url)
        # print_test("Save To Folder - Gfycat - Video Url : {}".format(video_url))
        download_web_file(video_url, data_directory)
    elif data_domain == DataDomain.Youtube.value:
        video_url = get_video_url_from_youtube(data_url)
        # print_test("Save To Folder - Youtube - Video Url : {}".format(video_url))
        download_web_file(video_url, data_directory)
    elif data_domain == DataDomain.Streamable.value:
        video_url = get_video_url_from_streamable(data_url)
        # print_test("Save To Folder - Stremable - Video Url : {}".format(video_url))
        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        download_web_file_with_header(video_url, data_directory)


def reddit_dota_spider(max_page, download=False):
    print_test("Reddit Dota Spider - Max Page : {} - Download : {}".format(max_page, download))
    page_no = 1
    item_no = 1
    url = base_url
    while page_no <= max_page and url:
        source_code = requests.get(url, headers=headers)
        plain_text = source_code.text
        soup = BeautifulSoup(plain_text, "html.parser")
        for thing_div in soup.find_all('div', {'class': 'thing'}):
            data_url = thing_div.get('data-url')
            data_domain = thing_div.get('data-domain')
            title_p = thing_div.find('p', {'class': 'title'})
            title_a = title_p.find('a', {'class': 'title'})
            href = str(title_a.get('href'))
            if href.startswith('http://') or href.startswith('https://'):
                pass
            else:
                href = base_top_url + href
            title = title_a.string
            title_span = title_p.find('span', {'class': 'linkflairlabel'})
            category = None
            if title_span:
                category = title_span.string
            print("{}) Title : {}\nCategory : {}\nHref : {}".format(item_no, title, category, href))
            print_test("Data Url : {}\nData Domain : {}".format(data_url, data_domain))
            # // TODO : start downloads in another thread
            if download:
                # print_test("Spider dl - data_domain : {}".format(data_domain))
                if data_domain in videoDomains or data_domain in imgDomains:
                    save_to_folder(data_domain, data_url, title, category)
            item_no += 1
        try:
            next_button_span = soup.find('span', {'class', 'next-button'})
            next_button_a = next_button_span.findChildren()
            next_page_url = next_button_a[0].get('href')
            # print_test(next_page_url)
        except:
            next_page_url = ''
        page_no += 1
        url = next_page_url


print_test("Command Line Args : {}".format(parser.parse_args()))
if args.max_page and args.download:
    reddit_dota_spider(args.max_page, str_to_bool(args.download))
elif args.max_page:
    reddit_dota_spider(args.max_page, True)
else:
    reddit_dota_spider(4, False)
input("Press any key to exit..")



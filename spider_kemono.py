import requests
import os
import urllib3
import threading
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urlsplit


# 禁用InsecureRequestWarning警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# 当前文件的绝对路径
base_file = os.path.abspath(__file__)

# 获取文件的文件夹信息
base_dir = os.path.dirname(base_file)

# 循环回合
rally = 0


# 预定义不允许的字符
INVALID_CHARS = r'[<>:"/\\|?*]'

# 清理文件夹名称 去掉windows不允许的文件夹字符
def clean_folder_name(folder_name):
    return re.sub(INVALID_CHARS, '_', folder_name)


# 下载单个图片的线程函数
def download_single_image(img_conf, save_path, img_name):
    
    # 最大重试次数
    max_retries=5
    # 重试次数
    retry_count = 0
    
    while retry_count < max_retries:
    
        try:
            
            img_response = requests.request(**img_conf)
            
            if img_response.status_code == 200:
                with open(save_path, 'wb') as img_file:
                    img_file.write(img_response.content)

                print(f"{img_name} 下载完成")
                return
            elif img_response.status_code == 429:
                
                retry_count += 1
                wait_time = 5 * retry_count  # 指数退避
                
                print(f"{img_name} 下载出错, 状态码为429。正在重试 {retry_count}/{max_retries}，等待 {wait_time} 秒...")
                
                time.sleep(wait_time)
            else:
                print(f"{img_name} 下载出错,状态码为{img_response.status_code}")
                return
            
        except Exception as e:
            print(f"{img_name} 下载出错: {e}")
            
    print(f"{img_name} 下载失败，已达最大重试次数 {max_retries}")



# 下载图片
def download_img(img_href, save_dir, href_title):
    img_href_conf = {
        'url': 'https://kemono.su' + img_href,
        'method': 'get',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A'
        },
        'proxies': {         # 代理
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        },
        'timeout': 60,
        'verify': False  # 忽略 SSL 错误
    }

    href_response = requests.request(**img_href_conf)

    href_soup = BeautifulSoup(href_response.text, 'lxml')

    print()
    print(f"开始下载{href_title}")
    print()

    count = 1

    # 定义线程池
    threads = []

    for img_url in href_soup.select('.post__files .post__thumbnail'):

        download_url = img_url.a['href']



        # 使用标题加上数字后缀来作为文件名
        img_file_name = os.path.basename(href_title + "-" + str(count))

        # 将url地址切割到文件名，最后由'.'切割为文件后缀
        _, img_file_extension = os.path.splitext(
            os.path.basename(urlsplit(download_url).path))

        # 图片名字
        img_name = img_file_name + img_file_extension

        save_path = os.path.join(save_dir, img_name)

        if os.path.exists(save_path):
            # img_conf = None
            print(img_name + " 已存在")
        else:
            # 图片下载的字典
            img_conf = {
                'url': download_url,
                'method': 'get',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A'
                },
                'proxies': {         # 代理
                    'http': 'http://127.0.0.1:7890',
                    'https': 'http://127.0.0.1:7890'
                },
                'timeout': 45,
                'verify': False  # 忽略 SSL 错误
            }
  
            # 多线程
            download_thread = threading.Thread(target=download_single_image, args=(img_conf, save_path, img_name))

            threads.append(download_thread)

            download_thread.start()

        count += 1

    # 线程加入线程池
    for thread in threads:
        thread.join()

    print()
    print(f"{href_title}下载完成")
    print()


# 爬虫
def spider(soup, author_path):
    # 使用标题为文件夹名称，网址还需要跳转

    for img in soup.select('.card-list__items .post-card'):
        title = img.header
        img_title = title.get_text(strip=True)
        
        # 清理文件夹名称
        clean_img_title = clean_folder_name(img_title)

        img_href = img.a['href']

        save_dir = os.path.join(author_path, clean_img_title)

        if os.path.exists(save_dir):
            pass
        else:
            os.makedirs(save_dir)

        # 图片分页链接，保存路径，分页标题，做图片标题
        download_img(img_href, save_dir, clean_img_title)


# 创建文件夹


def create_dir(soup, platform):

    result_dir_path = os.path.join(base_dir, "result")

    # 判定result目录是否存在
    if os.path.exists(result_dir_path):
        print(f"{result_dir_path}已存在")
    else:
        os.makedirs(result_dir_path)
        print(f"{result_dir_path}已创建")

    # 获取作者名
    author_name = soup.h1.get_text(strip=True)

    author_result_path = os.path.join(result_dir_path, author_name, platform)

    if os.path.exists(author_result_path):
        print(f"{author_name}/{platform}的目录已存在")
    else:
        os.makedirs(author_result_path)
        print(f"{author_name}/{platform}的目录已创建")

    # 开始爬虫
    spider(soup, author_result_path)


def main():
    
    
    # url中的页面标识
    work_num = 0

    while True:

        print("1.Pixiv Fanbox")
        print("2.Patreon")
        print("3.Fantia")
        print("4.Gumroad")
        platform = input("输入作者使用的赞助平台(默认为Patreon):")

        if platform == "1":
            platform = "fanbox"
        elif platform == "2":
            platform = "patreon"
        elif platform == "3":
            platform = "fantia"
        elif platform == "4":
            platform = "gumroad"
        else:
            platform = "patreon"

        author_id = input("输入Kemono作者id:")

        author_url = "https://kemono.su/" + platform + "/user/" + author_id + "?o=" + str(work_num)

        print()


        conf = {
            'url': author_url,
            'method': 'get',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A'
            },
            'proxies': {         # 代理
                'http': 'http://127.0.0.1:7890',
                'https': 'http://127.0.0.1:7890'
            },
            'verify': False  # 忽略 SSL 错误
        }

        # 接收回显信息
        response = requests.request(**conf)

        # 使用bs4接收
        soup = BeautifulSoup(response.text, 'lxml')

        print("连接状态: " + str(response.status_code))
        
        # 作者姓名
        author_name = soup.h1.get_text(strip=True)
        
        # 作者的作品数量情况
        author_artworks = soup.select_one('.paginator small').get_text(strip=True)
        author_artworks_num = author_artworks.split()[-1]
        
        
        # 循环回合
        rally = int(author_artworks_num) // 50
        
        # 取余
        rally_mod = int(author_artworks_num) % 50
        
        
        if (rally == 0) and (rally_mod != 0):
            rally += 1 

        choice = input(
            f"作者 {author_name} 的id为: {author_id} ,使用的赞助平台为: {platform} ,你确定吗?(y/n)")

        if choice == 'y':
            print()
            break
        else:
            print()

    conf = {
        'url': author_url,
        'method': 'get',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A'
        },
        'proxies': {         # 代理
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        },
        'verify': False  # 忽略 SSL 错误
        }
    
    for i in range(rally + 1):
        
        author_url = "https://kemono.su/" + platform + "/user/" + author_id + "?o=" + str(work_num)
        
        conf['url'] = author_url  # 更新conf中的URL
    
        response = requests.request(**conf)

        soup = BeautifulSoup(response.text, 'lxml')
        
        print(f"连接状态: {response.status_code}")

        create_dir(soup, platform)
        
        work_num += 50
        
        print(f"{author_name}/{platform} 的作品至标识 {work_num} 已下载完成")


    print(f"{author_name}/{platform}的作品已下载完成")


if __name__ == "__main__":
    main()



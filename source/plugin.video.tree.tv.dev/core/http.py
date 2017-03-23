# -*- coding: utf-8 -*-

import os, re, sys, json, urllib, hashlib, traceback, urlparse
import xbmcup.app, xbmcup.db, xbmcup.system, xbmcup.net, xbmcup.parser, xbmcup.gui
import xbmc, cover, xbmcplugin, xbmcgui
from xbmcup.app import Item
from common import Render
from auth import Auth
from defines import *
from random import randint
import math

reload(sys)
sys.setdefaultencoding("UTF8")

try:
    cache_minutes = 60*int(xbmcup.app.setting['cache_time'])
except:
    cache_minutes = 0

class HttpData:

    def load(self, url):
        try:
            self.auth = Auth()
            self.cookie = self.auth.get_cookies()
            headers = {
                'Referer' : url
            }
            response = xbmcup.net.http.get(url, cookies=self.cookie, headers=headers)
        except xbmcup.net.http.exceptions.RequestException:
            print traceback.format_exc()
            return None
        else:
            if(response.status_code == 200):
                if(self.auth.check_auth(response.text) == False):
                    self.auth.autorize()
                return response.text
            return None

    def post(self, url, data):
        try:
            data
        except:
            data = {}
        try:
            self.auth = Auth()
            self.cookie = self.auth.get_cookies()
            headers = {
                'Referer' : url
            }
            response = xbmcup.net.http.post(url, data, cookies=self.cookie, headers=headers)
        except xbmcup.net.http.exceptions.RequestException:
            print traceback.format_exc()
            return None
        else:
            if(response.status_code == 200):
                if(self.auth.check_auth(response.text) == False):
                    self.auth.autorize()
                return response.text
            return None


    def ajax(self, url):
        try:
            self.auth = Auth()
            self.cookie = self.auth.get_cookies()
            headers = {
                'X-Requested-With'  : 'XMLHttpRequest',
                'Referer'           : SITE_URL
            }
            response = xbmcup.net.http.get(url, cookies=self.cookie, headers=headers)
            print url
        except xbmcup.net.http.exceptions.RequestException:
            print traceback.format_exc()
            return None
        else:
            return response.text if response.status_code == 200 else None

    def get_movies(self, url, page, classname='main_content_item', nocache=False, search="", itemclassname="item"):
        page = int(page)
        if(page > 0):
            url = SITE_URL+"/"+url.strip('/')+"/page/"+str(page+1)
        else:
            url = SITE_URL+"/"+url.strip('/')
        print url

        if(search != '' and page == 0):
            html = self.post(url, {'usersearch' : search, 'filter' : 'all'})
        else:
            html = self.load(url)

        #print html.encode('utf-8')

        if not html:
            return None, {'page': {'pagenum' : 0, 'maxpage' : 0}, 'data': []}
        result = {'page': {}, 'data': []}
        soup = xbmcup.parser.html(self.strip_scripts(html))
        #print soup
        result['page'] = self.get_page(soup)
        center_menu = soup.find('div', class_=classname)
        # print center_menu
        try:
            for div in center_menu.find_all('div', class_=itemclassname):
                if(search != ''):
                    href = None
                else:
                    href = div.find('h2').find('a')
                try:
                    quality = div.find('span', class_='quality_film_title').get_text().strip()
                except:
                    quality = ''

                dop_information = []
                try:
                    if(itemclassname == 'item_wrap'):
                        year = div.find('a', class_='fast_search').get_text().strip()
                    else:
                        year = div.find('div', class_='smoll_year').get_text().strip()
                    dop_information.append(year)
                except:
                    pass

                try:
                    if(itemclassname == 'item_wrap'):
                        genre = div.find('span', class_='section_item_list').get_text().strip()
                    else:
                        genre = div.find('div', class_='smoll_janr').get_text().strip()
                    dop_information.append(genre)
                except:
                    pass

                information = ''
                if(len(dop_information) > 0):
                    information = '[COLOR white]['+', '.join(dop_information)+'][/COLOR]'

                posters = div.find('div', class_='preview').find_all('img')

                movieposter = None
                for img in posters:
                    img_src = img.get('src')
                    if(img_src.find('http') != -1):
                        movieposter = img_src
                        if(search != ''):
                            href = img.parent
                        break

                if(href == None):
                    raise

                #костыль для закладок
                if(classname == 'book_mark_content'):
                    try:
                        movieposter = SITE_URL+posters[0].get('src')
                    except:
                        pass

                if(search != ''):
                    name = href.find('img').get('alt').strip()
                else:
                    name = href.get_text().strip()

                movie_url = href.get('href'),
                movie_id = re.compile('/film/([\d]+)-', re.S).findall(movie_url[0])[0]


                result['data'].append({
                        'url': movie_url,
                        'id': movie_id,
                        'quality': self.format_quality(quality),
                        'year': information,
                        'name': name,
                        'img': None if not movieposter else movieposter
                    })

            #print result['data']
        except:
            print traceback.format_exc()

        if(nocache):
            return None, result
        else:
            return cache_minutes, result


    def get_movie_info(self, url):

        movieInfo = {}
        movieInfo['no_files'] = None
        movieInfo['episodes'] = True
        movieInfo['movies'] = []
        movieInfo['resolutions'] = []
        movieInfo['page_url'] = url[0]

        url = SITE_URL+url[0]
        html = self.load(url)
        print url.encode('utf-8')

        if not html:
            movieInfo['no_files'] = 'HTTP error'
            return movieInfo

        html = html.encode('utf-8')
        soup = xbmcup.parser.html(self.strip_scripts(html))

        folders = soup.find('div', id='accordion_wrap').findAll('div', class_='accordion_item')
        #folders = soup.find('div', id='accordion_wrap').findAll('div', class_='folder_name')

        avalible_res = soup.find('div', id='film_object_params').find('span', class_='film_q_img').get_text()

        #подпер костылем, пусть не болеет
        quality_matrix = {
            'HD' : ['360', '480', '720', '1080'],
            'HQ' : ['360', '480', '720'],
            'SQ' : ['360', '480'],
            'LQ' : ['360']
        }

        if(avalible_res == None or avalible_res not in quality_matrix):
            avalible_res = 'HD'

        movies = {}
        for fwrap in folders:
            folder_id = fwrap.find('div', class_='folder_name').get('data-folder')
            movies[folder_id] = {}
            folder_items = fwrap.findAll('div', class_='film_title_link')
            for q in quality_matrix[avalible_res]:
                for item in folder_items:
                    movie_data = [item.find('a').get_text().encode('utf-8'), item.find('a').get('data-href')]
                    try:
                        movies[folder_id][q].append(movie_data)
                    except:
                        movies[folder_id][q] = []
                        movies[folder_id][q].append(movie_data)


        #print movies

        #js_string = re.compile("'source'\s*:\s*\$\.parseJSON\('([^\']+)'\)", re.S).findall(html)[0].decode('string_escape').decode('utf-8')
        #movies = json.loads(js_string, 'utf-8')
        #print movies
        if(movies != None and len(movies) > 0):
            for window_id in movies:
                current_movie = {'folder_title' : '', 'movies': {}}
                try:
                    current_movie['folder_title'] = soup.find('div', {'data-folder': str(window_id)}).find('a')\
                        .get('title').encode('utf-8')
                except:
                    current_movie['folder_title'] = xbmcup.app.lang[30113]

                sort_movies = sorted(movies[window_id].items(), key=lambda (k,v): int(k))
                for movie in sort_movies:
                    try:
                        current_movie['movies'][movie[0]].append(movie[1])
                    except:
                        current_movie['movies'][movie[0]] = []
                        current_movie['movies'][movie[0]].append(movie[1])

                for resulut in current_movie['movies']:
                    current_movie['movies'][resulut] = current_movie['movies'][resulut][0]
                    # if(len(current_movie['movies'][resulut]) > 1):
                    #     movieInfo['episodes'] = True

                movieInfo['movies'].append(current_movie)

            # movieInfo['movies'] = movies

            movieInfo['title'] = soup.find('h1', id='film_object_name').get_text()
            try:
                movieInfo['description'] = soup.find('div', class_='description').get_text().strip()
            except:
                movieInfo['description'] = ''

            try:
                movieInfo['fanart'] = SITE_URL+soup.find('div', class_='screen_bg').find('a').get('href')
            except:
                movieInfo['fanart'] = ''
            try:
                movieInfo['cover'] = soup.find('img', id='preview_img').get('src')
            except:
                movieInfo['cover'] = ''
            try:
                movieInfo['genres'] = []
                genres = soup.find('div', class_='list_janr').findAll('a')
                for genre in genres:
                   movieInfo['genres'].append(genre.get_text().strip())
                movieInfo['genres'] = ' / '.join(movieInfo['genres']).encode('utf-8')
            except:
                movieInfo['genres'] = ''

            try:
                results = soup.findAll('a', class_='fast_search')
                movieInfo['year'] = self.get_year(results)
            except:
                movieInfo['year'] = ''
            try:
                movieInfo['director'] = soup.find('span', class_='regiser_item').get_text().encode('utf-8')
            except:
                movieInfo['director'] = ''
        else:
            try:
                no_files = soup.find('div', class_='no_files').get_text().strip().encode('utf-8')
            except:
                no_files = 'Что-то пошло не так...'

            movieInfo['no_files'] = no_files

        return movieInfo

    def get_collections(self):
        url = SITE_URL+"/collection"
        html = self.load(url)
        if not html:
            return None, {'page': {'pagenum' : 0, 'maxpage' : 10}, 'data': []}
        html = html.encode('utf-8')
        result = {'page': {}, 'data': []}
        soup = xbmcup.parser.html(self.strip_scripts(html))
        wrap = soup.find('div', class_='main_content_item')
        try:
            for div in wrap.find_all('div', class_='item'):
                try:
                    preview_img = div.find('div', class_='preview').find('img').get('src')
                except:
                    preview_img = ''

                try:
                    movie_count = div.find('div', class_='item_content').find('span').get_text().strip()
                except:
                    movie_count = ''

                try:
                    href = div.find('div', class_='item_content').find('a')
                    name = href.get_text().strip()+(' (%s)' % movie_count if movie_count != '' else '')
                    href = href.get('href')
                except:
                    name = ''
                    href = ''

                result['data'].append({
                        'url': href,
                        'name': name,
                        'img': None if not preview_img else (SITE_URL + preview_img)
                    })

        except:
            print traceback.format_exc()

        return cache_minutes, result


    def get_bookmarks(self):
        url = "%s/users/profile/bookmark" % SITE_URL

        #self.ajax('%s/users/profile/addbookmark?name=%s' % (SITE_URL, BOOKMARK_DIR))

        html = self.load(url)
        if not html:
            return None, {'page': {'pagenum' : 0, 'maxpage' : 0}, 'data': []}
        html = html.encode('utf-8')
        result = {'page': {}, 'data': []}
        soup = xbmcup.parser.html(self.strip_scripts(html))
        wrap = soup.find('div', id='bookmark_list')

        try:
            for div in wrap.find_all('a'):
                try:
                    href = div.get('data-rel')
                    name = div.get_text().strip()
                except:
                    name = ''
                    href = ''

                result['data'].append({
                        'url': href,
                        'name': name,
                        'img': cover.treetv
                    })

        except:
            print traceback.format_exc()

        return None, result

    def get_year(self, results):
        for res in results:
            if(res.get('data-rel') == 'year1'):
                return res.get_text().encode('utf-8')
        return 0

    def strip_scripts(self, html):
        #удаляет все теги <script></script> и их содержимое
        #сделал для того, что бы html parser не ломал голову на тегах в js

        html = re.compile(r'([a-zA-Z0-9]{1,1})"([a-zA-Z0-9]{1,1})').sub("\\1'\\2", html)
        html = re.compile(r'<script[^>]*>(.*?)</script>', re.S).sub('', html)
        html = re.compile(r'</script>', re.S).sub('', html)
        html = re.compile(r'alt="(>+|src=")', re.S).sub('\\1', html)
        html = re.compile(r'title="(>+|src=")', re.S).sub('\\1', html)
        #print html.encode('utf-8')
        return html

    def format_quality(self, quality):
        qualitys = {'HD' : 'ff3BADEE', 'HQ' : 'ff59C641', 'SQ' : 'ffFFB119', 'LQ' : 'ffDE4B64'}
        if(quality in qualitys):
            return "[COLOR %s][%s][/COLOR]" % (qualitys[quality], quality)
        return ("[COLOR ffDE4B64][%s][/COLOR]" % quality if quality != '' else '')


    def get_page(self, soup):
        info = {'pagenum' : 0, 'maxpage' : 0}
        try:
            try:
                wrap  = soup.find('div', id='main_paginator')
                wrap.find('b')
            except:
                wrap  = soup.find('div', class_='paginationControl')

            info['pagenum'] = int(wrap.find('a', class_="active").get_text().encode('utf-8'))
            try:
                info['maxpage'] = int(wrap.find('a', class_='last').get('data-rel'))
            except:
                try:
                    try:
                        info['maxpage'] = int(os.path.basename(wrap.find('a', class_='next').get('href')))
                    except:
                        info['maxpage'] = wrap.find('a', class_='next').get('data-rel')
                except:
                    info['maxpage'] = info['pagenum']
        except:
            info['pagenum'] = 1
            info['maxpage'] = 1
            print traceback.format_exc()

        return info

class ResolveLink(xbmcup.app.Handler, HttpData, Render):
    def handle(self):
        item_dict = self.parent.to_dict()
        self.params = self.argv[0]

        #print self.params

        movieInfo = self.get_movie_info(['/film/'+self.params['page']])
        item_dict['cover'] = movieInfo['cover']
        item_dict['title'] = self.params['file']
        folder = self.params['folder'].encode('utf-8')
        resolution = self.params['resolution'].encode('utf-8')
        self.parent = Item(item_dict)

        # print folder
        # print resolution
        #
        # print movieInfo

        #return 'http://cdn.3tv.im/hls/2/films/15/22345/26557/720p_Outsiders.s01e01.mp4/index.m3u8'

        if(len(movieInfo['movies']) > 0):
            for movies in movieInfo['movies']:
                for q in movies['movies']:
                    if(q == resolution):
                        # print movies['folder_title'].encode('utf-8')
                        if(movies['folder_title'] == folder or folder == ''):
                            for episode in movies['movies'][q]:
                                if episode[0].find(self.params['file']) != -1:
                                    return self.get_play_url_guarded(episode[1], resolution)

        return None

    def get_play_url(self, url, resolution):
        parsed_url = urlparse.urlparse(self.get_iframe(url))
        pl_url = "http://%s/m3u8/%s.m3u8" % (parsed_url[1], url.split('/')[2])
        return self.get_selected_playlist(pl_url, resolution)

    def get_iframe(self, url):
        html = self.ajax(SITE_URL+url)
        html = html.encode('utf-8')
        soup = xbmcup.parser.html(self.strip_scripts(html))
        iframe_url = soup.find('iframe').get('src').encode('utf-8')
        self.ajax(iframe_url.replace('/?', '/list/?')) #если не загружать эту ссылку - не всегда отдает плейлист
        return iframe_url

    def get_selected_playlist(self, general_pl_url, resulution):
        html = self.ajax(general_pl_url)
        if not html: return None
        html = html.encode('utf-8').split("\n")
        return_next = False
        for line in html:
            if(return_next):
                print line
                return line
            if(line.find('x'+resulution) != -1):
                return_next = True

        return None

    def get_play_url_guarded(self, url, resolution):
        parsed_url = urlparse.urlparse(self.get_iframe(url))
        playerKeyParams = self.getPlayerKeyParams()
        source = self.initMainModule(url.split('/')[2], playerKeyParams)
        pl_url = source[0]['sources'][0]['src']
        
        return self.get_guarded_playlist(pl_url, resolution) + '|' + CORS_HEADER

    def getPlayerKeyParams(self):
        app_js = self.load('http://player.tree.tv/js/app.js');
        values = re.findall(r'var\s*(.*?)\s*=\s*(.*?);', app_js, re.DOTALL | re.MULTILINE)

        p = 2
        g = 293
        for value in values:
            if(value[0] == 'playerKeyParams'):
                g = float(re.findall(r'g: (\d+)',values[1][1])[0])
                p = float(re.findall(r'p: (\d+)',values[1][1])[0])
                break

        return {
            'g': g,
            'p': p
        }

    def sendCheckParams(self, playerKeyParams):
        playerKeyParams['key'] = randint(1,7)
        numClient = pow(playerKeyParams['g'], playerKeyParams['key']);
        clientKey = math.fmod(numClient, playerKeyParams['p']);

        try:
            response = xbmcup.net.http.post('http://player.tree.tv/guard/', { 'key' : clientKey }, allow_redirects=False)
        except xbmcup.net.http.exceptions.RequestException:
                print traceback.format_exc()
                return None

        self.cookie = response.cookies
        return json.loads(response.text)

    def initMainModule(self, fileId, playerKeyParams):
        
        self.cookie = {}
        serverData = self.sendCheckParams(playerKeyParams)

        if (serverData['p'] != playerKeyParams['p'] and serverData['g'] != playerKeyParams['g']):
            playerKeyParams['p'] = serverData['p']
            playerKeyParams['g'] = serverData['g']
            return self.initMainModule(fileId, playerKeyParams)
        else:
            b = pow(serverData['s_key'], playerKeyParams['key'])
            skc = math.fmod(b, serverData['p']);
            try:
                response = xbmcup.net.http.post('http://player.tree.tv/guard/guard/', {
                    'file': fileId,
                    'source': '1',
                    'skc': skc
                }, allow_redirects=False, cookies=self.cookie)
            except xbmcup.net.http.exceptions.RequestException:
                print traceback.format_exc()
                return None

            self.cookie = response.cookies
            try:
                jsonResponse = json.loads(response.text)
            except:
                return self.initMainModule(fileId, playerKeyParams)

            return jsonResponse

    def get_guarded_playlist(self, general_pl_url, resulution):
        try:
            html = xbmcup.net.http.get(general_pl_url, allow_redirects=False)
        except xbmcup.net.http.exceptions.RequestException:
            print traceback.format_exc()
            return None

        html = html.text.encode('utf-8').split("\n")
        return_next = False
        for line in html:
            if(return_next):
                print line
                return line
            if(line.find('x'+resulution) != -1):
                return_next = True

        return None
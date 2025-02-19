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
from collections import OrderedDict

reload(sys)
sys.setdefaultencoding("UTF8")

try:
    cache_minutes = 60*int(xbmcup.app.setting['cache_time'])
except:
    cache_minutes = 0

fingerprintKey = '46309efe7f245682cbce9cfdbab31fd8'
userAgent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.110 Safari/537.36'

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
            folder = fwrap.find('div', class_='folder_name')
            if not folder:
                continue
            folder_id = folder.get('data-folder')
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
        movie_id = url.split('/')[2]

        self.setFingerPrint()
        source = self.initMainModule(movie_id, playerKeyParams)
        sourceSorted = {}
        for item in source:
            for sources in item['sources']:
                sourceSorted[sources['point']] = sources['src']

        if not movie_id in sourceSorted:
            return None

        pl_url = sourceSorted[movie_id]
        
        return self.get_guarded_playlist(pl_url, resolution) + '|' + CORS_HEADER

    def setFingerPrint(self):
        data = OrderedDict()
        components = json.loads('[{"key":"user_agent","value":"'+userAgent+'"},{"key":"language","value":"en-US"},{"key":"color_depth","value":24},{"key":"pixel_ratio","value":1},{"key":"hardware_concurrency","value":2},{"key":"resolution","value":[1680,1050]},{"key":"available_resolution","value":[1680,1014]},{"key":"timezone_offset","value":-180},{"key":"session_storage","value":1},{"key":"local_storage","value":1},{"key":"indexed_db","value":1},{"key":"open_database","value":1},{"key":"cpu_class","value":"unknown"},{"key":"navigator_platform","value":"Linux x86_64"},{"key":"do_not_track","value":"unknown"},{"key":"regular_plugins","value":["Chrome PDF Viewer::::application/pdf~pdf","Shockwave Flash::Shockwave Flash 25.0 r0::application/x-shockwave-flash~swf,application/futuresplash~spl","Widevine Content Decryption Module::Enables Widevine licenses for playback of HTML audio/video content. (version: 1.4.8.970)::application/x-ppapi-widevine-cdm~","Native Client::::application/x-nacl~,application/x-pnacl~","Chrome PDF Viewer::Portable Document Format::application/x-google-chrome-pdf~pdf"]},{"key":"canvas","value":"canvas winding:yes~canvas fp:data:image/png;base64,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IECAAAECBAgQIECAAAECBAgQIECgFnCg18LyCRAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQOBCwIF+MZOSBAgQIECAAAECBAgQIECAAAECBAgQIECAAAECBAgQIFALONBrYfkECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgcCHgQL+YSUkCBAgQIECAAAECBAgQIECAAAECBAgQIECAAAECBAgQqAUc6LWwfAIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBC4EHCgX8ykJAECBAgQIECAAAECBAgQIECAAAECBAgQIECAAAECBAjUAg70Wlg+AQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECFwIONAvZlKSAAECBAgQIECAAAECBAgQIECAAAECBAgQIECAAAECBGoBB3otLJ8AAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIELgQc6BczKUmAAAECBAgQIECAAAECBAgQIECAAAECBAgQIECAAAECtYADvRaWT4AAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIXAg70i5mUJECAAAECBAgQIECAAAECBAgQIECAAAECBAgQIECAAIFawIFeC8snQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAgQsBB/rFTEoSIECAAAECBAgQIECAAAECBAgQIECAAAECBAgQIECAQC0wIZHiQER7huMAAAAASUVORK5CYII="},{"key":"webgl","value":"data:image/png;base64,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~extensions:ANGLE_instanced_arrays;EXT_blend_minmax;EXT_disjoint_timer_query;EXT_frag_depth;EXT_shader_texture_lod;EXT_sRGB;EXT_texture_filter_anisotropic;WEBKIT_EXT_texture_filter_anisotropic;OES_element_index_uint;OES_standard_derivatives;OES_texture_float;OES_texture_float_linear;OES_texture_half_float;OES_texture_half_float_linear;OES_vertex_array_object;WEBGL_compressed_texture_s3tc;WEBKIT_WEBGL_compressed_texture_s3tc;WEBGL_debug_renderer_info;WEBGL_debug_shaders;WEBGL_depth_texture;WEBKIT_WEBGL_depth_texture;WEBGL_draw_buffers;WEBGL_lose_context;WEBKIT_WEBGL_lose_context~webgl aliased line width range:[1, 8192]~webgl aliased point size range:[0, 8192]~webgl alpha bits:8~webgl antialiasing:yes~webgl blue bits:8~webgl depth bits:24~webgl green bits:8~webgl max anisotropy:16~webgl max combined texture image units:48~webgl max cube map texture size:8192~webgl max fragment uniform vectors:4096~webgl max render buffer size:8192~webgl max texture image units:16~webgl max texture size:8192~webgl max varying vectors:32~webgl max vertex attribs:16~webgl max vertex texture image units:16~webgl max vertex uniform vectors:4096~webgl max viewport dims:[8192, 8192]~webgl red bits:8~webgl renderer:WebKit WebGL~webgl shading language version:WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)~webgl stencil bits:0~webgl vendor:WebKit~webgl version:WebGL 1.0 (OpenGL ES 2.0 Chromium)~webgl unmasked vendor:X.Org~webgl unmasked renderer:Gallium 0.4 on AMD RV770 (DRM 2.46.0 / 4.8.0-45-generic, LLVM 3.8.1)~webgl vertex shader high float precision:23~webgl vertex shader high float precision rangeMin:127~webgl vertex shader high float precision rangeMax:127~webgl vertex shader medium float precision:23~webgl vertex shader medium float precision rangeMin:127~webgl vertex shader medium float precision rangeMax:127~webgl vertex shader low float precision:23~webgl vertex shader low float precision rangeMin:127~webgl vertex shader low float precision rangeMax:127~webgl fragment shader high float precision:23~webgl fragment shader high float precision rangeMin:127~webgl fragment shader high float precision rangeMax:127~webgl fragment shader medium float precision:23~webgl fragment shader medium float precision rangeMin:127~webgl fragment shader medium float precision rangeMax:127~webgl fragment shader low float precision:23~webgl fragment shader low float precision rangeMin:127~webgl fragment shader low float precision rangeMax:127~webgl vertex shader high int precision:0~webgl vertex shader high int precision rangeMin:31~webgl vertex shader high int precision rangeMax:30~webgl vertex shader medium int precision:0~webgl vertex shader medium int precision rangeMin:31~webgl vertex shader medium int precision rangeMax:30~webgl vertex shader low int precision:0~webgl vertex shader low int precision rangeMin:31~webgl vertex shader low int precision rangeMax:30~webgl fragment shader high int precision:0~webgl fragment shader high int precision rangeMin:31~webgl fragment shader high int precision rangeMax:30~webgl fragment shader medium int precision:0~webgl fragment shader medium int precision rangeMin:31~webgl fragment shader medium int precision rangeMax:30~webgl fragment shader low int precision:0~webgl fragment shader low int precision rangeMin:31~webgl fragment shader low int precision rangeMax:30"},{"key":"adblock","value":true},{"key":"has_lied_languages","value":false},{"key":"has_lied_resolution","value":false},{"key":"has_lied_os","value":false},{"key":"has_lied_browser","value":false},{"key":"touch_support","value":[0,false,false]},{"key":"js_fonts","value":["Arial","Courier","Courier New","Helvetica","Times","Times New Roman"]}]')
        index = 0
        data['result'] = fingerprintKey
        self.cookie = {'mycook': fingerprintKey}
        for item in components:
            data['components['+str(index)+'][key]'] = str(item['key'])
            if isinstance(item['value'], list):
                data['components['+str(index)+'][value][]'] = item['value']
            else:
                data['components['+str(index)+'][value]'] = str(item['value'])
            index = index + 1

        
        try:
            response = xbmcup.net.http.post('http://tree.tv/film/index/imprint', data, allow_redirects=False, headers={
                'X-Requested-With':'XMLHttpRequest',
                'User-Agent': userAgent
            }, cookies=self.cookie)
        except xbmcup.net.http.exceptions.RequestException:
                print traceback.format_exc()
                return None

        self.cookie = response.cookies

    def getPlayerKeyParams(self):
        app_js = self.load('http://player.tree.tv/js/main.min.js');       
        # playerKeyParams={key:null,g:2,p:293}
        values = re.findall(r'playerKeyParams\s*=\s*{.*?}', app_js, re.DOTALL | re.MULTILINE)
        
        p = 2
        g = 293

        if values:
            g = float(re.findall(r'g:\s*(\d+)',values[0])[0])
            p = float(re.findall(r'p:\s*(\d+)',values[0])[0])
        
        return {
            'g': g,
            'p': p
        }

    def sendCheckParams(self, playerKeyParams):
        playerKeyParams['key'] = randint(1,7)
        numClient = pow(playerKeyParams['g'], playerKeyParams['key']);
        clientKey = math.fmod(numClient, playerKeyParams['p']);
        self.cookie.set('mycook', fingerprintKey)

        try:
            response = xbmcup.net.http.post('http://player.tree.tv/guard/', { 'key' : clientKey }, allow_redirects=False, cookies=self.cookie)
        except xbmcup.net.http.exceptions.RequestException:
            print traceback.format_exc()
            return None

        #self.cookie = response.cookies

        return json.loads(response.text)

    def initMainModule(self, fileId, playerKeyParams):
        
        serverData = self.sendCheckParams(playerKeyParams)

        if (serverData['p'] != playerKeyParams['p'] and serverData['g'] != playerKeyParams['g']):
            playerKeyParams['p'] = serverData['p']
            playerKeyParams['g'] = serverData['g']
            return self.initMainModule(fileId, playerKeyParams)
        else:
            b = pow(serverData['s_key'], playerKeyParams['key'])
            skc = math.fmod(b, serverData['p']);

            self.cookie.set('mycook', fingerprintKey)

            try:
                response = xbmcup.net.http.post('http://player.tree.tv/guard/guard/', {
                    'file': fileId,
                    'source': '1',
                    'skc': skc
                }, allow_redirects=False, cookies=self.cookie, headers={
                    'X-Requested-With':'XMLHttpRequest',
                    'User-Agent': userAgent
                })
            except xbmcup.net.http.exceptions.RequestException:
                print traceback.format_exc()
                return None

            try:
                jsonResponse = json.loads(response.text)
            except:
                return self.initMainModule(fileId, playerKeyParams)

            return jsonResponse

    def get_guarded_playlist(self, general_pl_url, resulution):
        self.cookie.set('mycook', fingerprintKey)
        try:
            html = xbmcup.net.http.get(general_pl_url, allow_redirects=False, cookies=self.cookie, headers={'User-Agent': userAgent})
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
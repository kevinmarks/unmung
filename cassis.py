# -*- coding: utf-8 -*-

import re
import sys
import os.path
import urllib

if sys.version < '3':
    from urlparse import urlparse
else:
    from urllib.parse import urlparse
    xrange = range


def auto_link_re():
    return re.compile('(?:\\@[_a-zA-Z0-9]{1,17})|(?:(?:(?:(?:http|https|irc)?:\\/\\/(?:(?:[!$&-.0-9;=?A-Z_a-z]|(?:\\%[a-fA-F0-9]{2}))+(?:\\:(?:[!$&-.0-9;=?A-Z_a-z]|(?:\\%[a-fA-F0-9]{2}))+)?\\@)?)?(?:(?:(?:[a-zA-Z0-9][-a-zA-Z0-9]*\\.)+(?:(?:aero|arpa|asia|a[cdefgilmnoqrstuwxz])|(?:biz|b[abdefghijmnorstvwyz])|(?:cat|com|coop|c[acdfghiklmnoruvxyz])|d[ejkmoz]|(?:edu|e[cegrstu])|f[ijkmor]|(?:gov|g[abdefghilmnpqrstuwy])|h[kmnrtu]|(?:info|int|i[delmnoqrst])|j[emop]|k[eghimnrwyz]|l[abcikrstuvy]|(?:mil|museum|m[acdeghklmnopqrstuvwxyz])|(?:name|net|n[acefgilopruz])|(?:org|om)|(?:pro|p[aefghklmnrstwy])|qa|r[eouw]|s[abcdeghijklmnortuvyz]|(?:tel|travel|t[cdfghjklmnoprtvwz])|u[agkmsyz]|v[aceginu]|w[fs]|y[etu]|z[amw]))|(?:(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[1-9])\\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[0-9])\\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[0-9])\\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[0-9])))(?:\\:\\d{1,5})?)(?:\\/(?:(?:[!#&-;=?-Z_a-z~])|(?:\\%[a-fA-F0-9]{2}))*)?)(?=\\b|\\s|$)', flags=re.IGNORECASE)
    # ccTLD compressed regular expression clauses (re)created.
    # .mobi .jobs deliberately excluded to discourage layer violations.
    # see http://flic.kr/p/2kmuSL for more on the problematic new gTLDs
    # part of $re derived from Android Open Source Project, Apache 2.0
    # with a bunch of subsequent fixes/improvements (e.g. ttk.me/t44H2)
    # thus auto_link_re is also Apache 2.0 licensed
    # http://www.apache.org/licenses/LICENSE-2.0
    # - Tantek 2010-046 (moved to auto_link_re 2012-062)


def auto_link(text, do_embed=False,maxUrlLength=0):
    """ auto_link: param 1: text; param 2: do embeds or not
    auto_link is idempotent, works on plain text or typical markup.
    """
    regex = auto_link_re()
    ms = regex.findall(text)
    if not ms:
        return text

    mlen = len(ms)
    sp = regex.split(text)

    text = ''
    for i in xrange(mlen):
        mi = ms[i]
        spliti = sp[i]
        text = text + spliti

        if sp[i + 1].startswith('/'):  # regex omits end/ before </a
            sp[i + 1] = sp[i + 1][1:]
            mi = mi + '/'  # include / in the match

        spe = spliti[-2:]
        # avoid 2x-linking, don't link CSS @-rules, attr values, asciibet
        if ((not spe or not re.match('(?:\\=[\\"\\\']?|t;)', spe)) and
            sp[i + 1].strip()[:3] != '</a' and
            (mi not in ['charset', 'font', 'font-face', 'import', 'media',
                        'namespace', 'page', 'ABCDEFGHIJKLMNOPQ'])):
            afterlink = ''
            afterchar = mi[-1]
            while (afterchar in '.!?,;"\')]}' and  # trim punc from
                   (afterchar != ')' or '(' not in mi)):  # 1 () pair
                afterlink = afterchar + afterlink
                mi = mi[:-1]
                afterchar = mi[-1]

            fe = 0
            if do_embed:
                _, fe = os.path.splitext(mi.lower())

            wmi = web_address_to_uri(mi, True)
            wp = urlparse(wmi)
            prot = wp.scheme + ':'
            hn = wp.netloc
            pa = wp.path
            ih = wmi.startswith('http')
            displayUrl = mi
            if maxUrlLength:
                displayUrl = wp.netloc+wp.path
                if wp.query:
                    displayUrl = displayUrl + '?'+wp.query
                if len(displayUrl)> maxUrlLength:
                    shortUrl = unicode(displayUrl[:maxUrlLength])+u'…'
                    displayUrl = shortUrl.encode('utf-8')
            if (fe and
                (fe == '.jpeg' or fe == '.jpg' or fe == '.png' or
                 fe == '.gif' or fe == '.svg')):
                alt = 'a ' + 'photo' if 'photo' in mi else fe[1:]
                text = (text + '<a class="auto-link figure" href="' +
                        wmi + '"><img alt="' + alt + '" src="' +
                        wmi + '"/></a>' + afterlink)
            elif fe and (fe == '.mp4' or fe == '.mov' or fe == '.ogv'):
                text = (text + '<a class="auto-link figure" href="' +
                        wmi, '"><video controls="controls" src="' +
                        wmi, '"></video></a>' + afterlink)
            elif ih and hn == 'vimeo.com' and pa[1:].isdigit():
                text = (text + '<a class="auto-link" href="' +
                        wmi + '">' + displayUrl + '</a> <iframe class="vimeo-player auto-link figure" width="480" height="385" style="border:0" src="' + prot + '//player.vimeo.com/video/' +
                        pa[1:] + '"></iframe>' + afterlink)
            elif (hn == 'youtu.be' or
                  ((hn == 'youtube.com' or hn == 'www.youtube.com')
                   and 'watch?v=' in mi)):
                if hn == 'youtu.be':
                    yvid = pa[1:]
                else:
                    offs = mi.index('watch?v=')
                    yvid = mi[offs + 8:].split('&', 1)[0]

                text = (text + '<a class="auto-link" href="' +
                        wmi + '">' + displayUrl + '</a> <iframe class="youtube-player auto-link figure" width="480" height="385" style="border:0" src="' + prot + '//www.youtube.com/embed/' +
                        yvid + '"></iframe>' +
                        afterlink)
            elif mi.startswith('@'):
                if (sp[i + 1][:1] == '.' and
                        spliti != '' and ctype_email_local(spliti[-1])):
                    # if email address, simply append info, no linking
                    text = text + displayUrl + afterlink

                else:
                    # treat it as a Twitter @-username reference and link it
                    text = (text + '<a class="auto-link h-x-username" href="' +
                            wmi + '">' + displayUrl + '</a>' +
                            afterlink)

            elif wp.fragment:
                fragmentioned = urllib.unquote_plus(wp.fragment)
                if ' ' in fragmentioned and do_embed:
                    if fragmentioned.startswith('#'):
                        fragmentioned = fragmentioned[1:]
                    text = (text + '<blockquote class="auto-mention"><a class="auto-link" href="' +
                        wmi + '"><cite>' + wp.netloc +'</cite><p>' + fragmentioned
                         + '</p></a></blockquote>' + afterlink)
            else:
                text = (text + '<a class="auto-link" href="' +
                        wmi + '">' + displayUrl + '</a>' +
                        afterlink)
        else:
            text = text + mi

    return text + sp[mlen]


def web_address_to_uri(wa, addhttp=False):
    if (not wa or wa.startswith('http://')
            or wa.startswith('https://')
            or wa.startswith('irc://')):
        return wa

    if (wa.startswith('Http://') or wa.startswith('Https://')):
        # handle iOS4 overcapitalization of input entries
        return 'h' + wa[1:]

    # TBI: may want to handle typos as well like:
    # missing/extra : or / http:/ http///
    # missing letter in protocol: ttps htps htts, ttp htp htt, ir ic rc
    # use strtolower(substr($wa, 0, 6)); // handle capitals in URLs
    if wa[0] == '@':
        return 'https://twitter.com/' + wa[1:]

    if addhttp:
        wa = 'http://' + wa

    return wa


def ctype_email_local(s):
    """close enough. no '.' because this is used for last char of.
    """
    return re.match("^[a-zA-Z0-9_%+-]+$", s)


if __name__ == '__main__':
    text = auto_link("it's pretty interesting how twitter auto-links it... http://example.com/a_link_(with_parens) vs. (http://example.com/a_link_without)")
    print(text)

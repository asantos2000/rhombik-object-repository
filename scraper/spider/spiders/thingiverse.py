# -*- coding: utf-8 -*-
import scrapy
from scrapy.contrib.spiders import CrawlSpider, Rule
from scraper.spider.items import ProjectItem, fileObjectItem
from scrapy.contrib.linkextractors import LinkExtractor
import re
import urlparse

from twisted.internet import reactor
from scrapy.crawler import Crawler
from scrapy import log, signals
from scrapy.utils.project import get_project_settings
from django.contrib.auth.models import User

import os
os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "scraper.spider.settings")


def runScraper(urls, user):
    userID=user.pk
    spider = ThingiverseSpider(urls, user=user)
    settings = get_project_settings()
    crawler = Crawler(settings)
    crawler.signals.connect(reactor.stop, signal=signals.spider_closed)
    crawler.configure()
    crawler.crawl(spider)
    crawler.start()
    reactor.run(installSignalHandlers=0)

class ThingiverseSpider(CrawlSpider):
    name = "thingiverse"
    allowed_domains = ["thingiverse.com"]
    download_delay = 0.4
    ##Find the links.
    start_urls = None
    def __init__(self, start_urls, user=None, *args, **kwargs):
        self.start_urls = start_urls
	if not user:
            user = User.objects.filter(pk=1)[0]
	self.user_id=user.pk
        super(ThingiverseSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        requests=[]
        for i in self.start_urls:
            requests.append(scrapy.http.Request(url=i, callback=self.parse, dont_filter=True))
        return requests

    def parse(self, response):
        ## if it's a thing it's not a profile.
        if re.search('thing:\d\d+',response.url):
            yield scrapy.http.Request(url=response.url, callback=self.project)
        else:
            ## sometimes thing pages link to other things with the 'design' tag. I haven't seen this on a user page.
            design = LinkExtractor(allow=('design')).extract_links(response)
            if design:  
                yield scrapy.http.Request(url=design[0].url, callback=self.projectGet)

    def projectGet(self, response):
        ##Get next pages. We can be really lazy due to the scrapy dedupe
        paginatorlinks=response.selector.xpath('//*[contains(@class,\'pagination\')]/ul/li/a/@href').extract()
        #:/ I guess this makes sense.
        from exceptions import IndexError
        try:
            paginatorlinks.pop(0)
        except IndexError as e:
            # e.message is dep, I guess using str(e) returning the message now is the thing.
            if not str(e) == "pop from empty list":
                raise
        for i in paginatorlinks:
            yield scrapy.http.Request(url=urlparse.urljoin(response.url, i), callback=self.projectGet)

        objects = LinkExtractor(allow=('thing:\d\d+')).extract_links(response)
        for i in objects:
            # Teh hax! scrapy's dupefilter sees "foo.bar" and "foo.bar/" as different sites. This is bad. Maybe this should be pushed to scrapy proper...
            if i.url[-1] == '/':
                i.url=i.url[:-1]
            yield scrapy.http.Request(url=i.url, callback=self.project)

###This is where we get items. Everything else is just URL handling.

    def project(self,response):
	
	## Get the project info proper.
        projectObject=ProjectItem()
        projectObject['author']=User.objects.get(pk=self.user_id)
        projectObject['title']=response.selector.xpath('//*[contains(@class,\'thing-header-data\')]/h1/text()').extract()[0].strip()
        projectObject['tags'] = response.selector.xpath("//*[contains(@class,\'thing-info-content thing-detail-tags-container\')]/div/a/text()").extract()
        yield projectObject

	## get special text files. (readme, instructions, license)
        import html2text
        h2t = html2text.HTML2Text()
        #Get the reame file, do stuff to it.
        readme = h2t.handle(response.selector.xpath("//*[@id = 'description']").extract()[0].strip())
	import unicodedata
	readmeItem=fileObjectItem()
	readmeItem["name"]="README.md"
	readmeItem["parent"]=projectObject['SID']
	readmeItem["filename"]=u""+unicodedata.normalize('NFKD',readme).encode('ascii','ignore')
        readmeItem['isReadme'] = True
        yield readmeItem
        #projectObject['readme'] = u""+unicodedata.normalize('NFKD',readme).encode('ascii','ignore')
        #also a markdown file I guess we'd want.
        try:
            instructions = u""+h2t.handle(response.selector.xpath("//*[@id = 'instructions']").extract()[0].strip()).encode('ascii','ignore')
            instructionItem=fileObjectItem()
            instructionItem["name"]="Instructions.md"
            instructionItem["parent"]=projectObject['SID']
            instructionItem["filename"]=instructions
            yield instructionItem
        except IndexError:
            pass
            #print("xpath to get the instructions IndexError'd")

        ## now, because the format of the license on thingi is always the same, we can pull this off.
        ## but I expect it is rather fragile.
        licenseurl =response.selector.xpath("//*[contains(@class,\'license-text\')]/a/@href")[2].extract().strip()
        licensetext = response.selector.xpath("//*[contains(@class,\'license-text\')]/a/text()")[1].extract().strip()
        licenceItem=fileObjectItem()
        licenceItem["name"]="License.md"
        licenceItem["parent"]=projectObject['SID']
        licenceItem["filename"]="["+licensetext+"]("+licenseurl+")"
        yield licenceItem

	## get all the projects image and file objects
        filelist = response.selector.xpath('//*[contains(@class,\'thing-file\')]/a/@href')
        for i in filelist:
        	yield scrapy.http.Request(url=urlparse.urljoin(response.url, i.extract()), callback=self.item, meta={'parent':projectObject['SID']})

        #Grab only raw images.        
        imagelist = response.selector.xpath('//*[contains(@class,\'thing-gallery-thumbs\')]/div[@data-track-action="viewThumb"][@data-thingiview-url=""]/@data-large-url')
        for i in imagelist:
            yield scrapy.http.Request(dont_filter=True, url=urlparse.urljoin(response.url, i.extract()), callback=self.item, meta={'parent':projectObject['SID']})

    def closed(self, *args, **kwargs):
        from scraper.spider import djangoAutoItem
        from project.models import Project
        from exceptions import KeyError
        for key in djangoAutoItem.SIDmap:
            project=Project.objects.get(pk=djangoAutoItem.SIDmap[key]['pk'])
            project.save(enf_valid=True)


    def item(self,response):
        item=fileObjectItem()

        ## warning stupid preasent here.
	# splitting and grabing from urlparse for filename may not be best.
        item['name']=urlparse.urlparse(response.url)[2].split("/")[-1]
	item['name']=item['name'].replace("_display_large","")

        item['parent'] = response.meta['parent']
        item['filename']=response.body
        yield(item)


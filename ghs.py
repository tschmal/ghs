#!/usr/bin/python
# -*- coding: utf-8 -*-

import praw
import requests
import time
import calendar
import yaml
import HTMLParser
import sys
import os
from ConfigParser import SafeConfigParser

def get_config():
  cfg = SafeConfigParser()
  cfg_path = os.path.abspath(os.path.dirname(sys.argv[0]))
  cfg_path = os.path.join(cfg_path, 'ghs.cfg')
  cfg.read(cfg_path)
  return cfg

def now():
  return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def get_upcoming_events(calendar_id, calendar_token):
  r = requests.get("https://www.googleapis.com/calendar/v3/calendars/" + calendar_id + "/events", params={
    "maxResults": 5,
    "orderBy": "startTime",
    "singleEvents": "true",
    "fields": "items(location,start,summary,description),summary",
    "timeMin": now(),
    "key": calendar_token
  })
  
  for item in r.json()["items"]:
    yield item

def format_timestamp(event):
  current_time = time.time()
  event_time = calendar.timegm(time.strptime(event["start"]["dateTime"], "%Y-%m-%dT%H:%M:%SZ"))

  if current_time >= event_time - 60:
    return "[**LIVE**](#live)"
  else:
    def format_segment(number, suffix=""):
      return "%d%s" % (number, suffix) if number else ""

    time_diff = event_time - current_time
    days = time_diff // 86400
    hours = (time_diff % 86400) // 3600
    minutes = (time_diff % 3600) // 60

    return " ".join([format_segment(days, "d"), format_segment(hours, "h"), format_segment(minutes, "m")]).strip()

def format_event(event):
  name_md = u""
  properties = {}

  if "description" in event:
    properties = yaml.safe_load(event["description"])

  # Show the icon depending on the type of the event
  event_type = properties.get("type", "show")
  if event_type == "show":
    pass
  elif event_type == "show":
    name_md += u"[♫] "
  else:
    name_md += u"[♛] ";

  # Event name
  if "location" in event:
    name_md += "**[" + event["summary"] + "](" + event["location"] + ")**"
  else:
    name_md += "**" + event["summary"] + "**"

  # Tagline
  if "description" in properties:
    name_md += "  \n  %s" % (properties["description"])
  
  return name_md


def main():
  cfg = get_config()
  h = HTMLParser.HTMLParser()

  while True:
    try:
      r = praw.Reddit(user_agent="ghs/2.0")
      r.set_oauth_app_info(client_id=cfg.get('reddit', 'oauth_client_id'),
        client_secret=cfg.get('reddit', 'oauth_client_secret'),
        redirect_uri="")
      r.login(cfg.get('reddit', 'username'), cfg.get('reddit', 'password'))
      break
    except Exception as e:
      print "ERROR: {0}".format(e)

  while True:
    try:
      print "fetching calendar data"
      events_md = ""
      for event in get_upcoming_events(cfg.get('calendar', 'id'), cfg.get('google', 'token')):
        events_md += "* %s  \n  %s\n\n" % (format_timestamp(event), format_event(event))

      print "fetching sidebar template"
      subreddit = r.get_subreddit(cfg.get('reddit', 'subreddit'))
      template_md = h.unescape(subreddit.get_wiki_page("sidebar").content_md)

      print "updating sidebar"
      sidebar_md = template_md.replace("{{events}}", events_md)
      subreddit.edit_wiki_page("config/sidebar", sidebar_md)

      print "sleeping for 60 seconds"
      time.sleep(60)
    except KeyboardInterrupt:
      raise
    except Exception as e:
      print "ERROR: {0}".format(e)

if __name__ == '__main__':
  main()
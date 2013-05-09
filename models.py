__author__ = 'benjaminechols'


class SiteStats:
    stats = None
    total_hash_rate = 0.0
    hash_samples = 0.0
    dead_workers = ()

    name = ""
    api_key = ""

    height = 0
    def __init__(self, name, api_key):
        self.name = name
        self.api_key = api_key
        self.dead_workers = {}
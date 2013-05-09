__author__ = 'benjaminechols'


class SiteStats:
    stats = None

    last_hashrate = 0.0
    total_hash_rate = 0.0
    hash_samples = 0.0

    dead_workers = ()

    name = ""
    api_key = ""

    height = 0

    worker_stats = None

    def __init__(self, name, api_key):
        self.name = name
        self.api_key = api_key
        self.dead_workers = {}
        self.worker_stats = {}

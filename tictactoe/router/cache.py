import random


CACHE_SIZE = 10240


class RandomChoiceDict(dict):

    def __init__(self):
        self.id2key = {}
        self.key2id = {}

    def __setitem__(self, key, value):
        if key not in self:
            new_id = len(self)
            self.id2key[new_id] = key
            self.key2id[key] = new_id
        super(RandomChoiceDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        super(RandomChoiceDict, self).__delitem__(key)

        empty_id = self.key2id[key]
        largest_id = len(self)
        largest_id_key = self.id2key[largest_id]
        self.id2key[empty_id] = largest_id_key
        self.key2id[largest_id_key] = empty_id

        del self.key2id[key]
        del self.id2key[largest_id]

    def pop_random(self):
        r = random.randrange(len(self))
        k = self.id2key[r]
        ret = self[k]
        super(RandomChoiceDict, self).__delitem__(k)
        return k, ret


class Cache(object):

    def __init__(self):
        self.data = RandomChoiceDict()


    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
        if len(self.data) > CACHE_SIZE:
            self.data.pop_random()

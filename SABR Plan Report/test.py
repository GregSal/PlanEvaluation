


class test():
    def __init__(self, name=None):
        self.name = name

class int2(dict):
    def __init__(self, name, number):
        super().__init__()
        pass

a= int2('hi', 1)

class intTest(int, test):
    def __init__(self, name, number):
        int.__init__(self)
        # test.__init__(self.name)
        print('Hi')

b= intTest('hi', 1)

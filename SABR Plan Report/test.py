


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

text = 'V 2800 cGy'
text2 = 'Maximum'
contruct_pattern = (
    r'^(?P<target>[DV])\s'  # Target type: D for dose of V for volume
    r'(?P<value>\d+\.?\d)\s'  # Search value a decimal or integer
    r'(?P<unit>\w+)$'           # Units of search value
    )
re_construct = re.compile(contruct_pattern)
value_constructor = re_construct.fullmatch(text)
re_construct.findall(text2)

import sys
sys.path.append('..')

from quickjs import JSRuntime, JSContext


def demo0():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.load('examples/yjs.js')

    Y = ctx['Y']
    # print(Y)

    doc1 = ctx.eval('new Y.Doc()')
    doc2 = ctx.eval('new Y.Doc()')

    doc1.on('update', lambda update, *_: Y.applyUpdate(doc2, update))
    doc2.on('update', lambda update, *_: Y.applyUpdate(doc1, update))

    # All changes are also applied to the other document
    doc1.getArray('myarray').insert(0, ['Hello doc2, you got this?'])
    print(doc2.getArray('myarray').get(0)) # => 'Hello doc2, you got this?'


def demo1():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.load('examples/yjs.js')

    Y = ctx['Y']
    # print(Y)

    doc1 = ctx.eval('new Y.Doc()')
    doc2 = ctx.eval('new Y.Doc()')

    doc1.getArray('myarray').insert(0, ['Hello doc2, you got this?'])

    state1 = Y.encodeStateAsUpdate(doc1)
    state2 = Y.encodeStateAsUpdate(doc2)
    Y.applyUpdate(doc1, state2)
    Y.applyUpdate(doc2, state1)

    print(doc2.getArray('myarray').get(0))


def demo2():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.load('examples/yjs.js')

    Y = ctx['Y']
    # print(Y)

    doc1 = ctx.eval('new Y.Doc()')
    doc2 = ctx.eval('new Y.Doc()')

    doc1.getArray('myarray').insert(0, ['Hello doc2, you got this?'])

    stateVector1 = Y.encodeStateVector(doc1)
    stateVector2 = Y.encodeStateVector(doc2)
    diff1 = Y.encodeStateAsUpdate(doc1, stateVector2)
    diff2 = Y.encodeStateAsUpdate(doc2, stateVector1)
    Y.applyUpdate(doc1, diff2)
    Y.applyUpdate(doc2, diff1)

    print(doc2.getArray('myarray').get(0))


if __name__ == '__main__':
    demo0()
    demo1()
    demo2()

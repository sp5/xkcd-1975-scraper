import aiohttp
import asyncio
import json
import io
import argparse

def dotquote(s):
    return '"{}"'.format(s.replace('\\', '\\\\').replace('"', '\\"'))

def dotlabel(a, lb):
    return '{} [label={}];'.format(dotquote(a), dotquote(lb))

traces = set()
def dotconnect(a, b, dirback=False, dashed=False):
    if (a, b) in traces:
        pass
    traces.add((a, b))

    if dirback or dashed:
        return '{} -> {} [{}];'.format(dotquote(a), dotquote(b),
                ','.join((('dir=back' if dirback else ''),
                          ('style=dashed' if dashed else ''))))
    else:
        return '{} -> {};'.format(dotquote(a), dotquote(b))

def combine(x, y):
    return str(x) + ':' + str(y)

async def get(session, url):
    async with session.get(url) as response:
        return json.loads(await response.text())

base = "https://xkcd.com/1975/alto/"

stuff = {}
async def get1975(session, what, which):
    if what not in stuff:
        stuff[what] = {}

    if which not in stuff[what]:
        stuff[what][which] = await get(session, base + what + '/' + which)

    return stuff[what][which]

labels = {}


stuff['menu'] = {}
async def rg(session):
    if 'root' not in stuff:
        stuff['root'] = await get(session, base + 'root')
    return stuff['root']

async def mg(session, which):
    return await get1975(session, 'menu', which)

async def recurse(session, start, sl, depth=3):
    if depth == 0: return

    actions = []
    for i, entry in enumerate(start['entries']):
        async def action(i, entry):
            try:
                label = entry['label']

                if 'subMenu' not in entry['reaction']:
                    idc = combine(sl, i)
                    print(dotlabel(idc, label))
                    print(dotconnect(sl, idc))
                    return

                submenu = entry['reaction']['subMenu']
                if submenu in stuff['menu']:
                    if label == labels[submenu]:
                        dotconnect(sl, submenu, dirback=True)
                    else:
                        idc = combine(sl, i)
                        print(dotlabel(idc, label))
                        print(dotconnect(sl, idc))
                        print(dotconnect(submenu, idc, dirback=True,
                            dashed=True))
                    return

                try:
                    sub_tree = await mg(session, submenu)
                except Exception as e:
                    eidc = combine(submenu, 'error')
                    print(dotlabel(eidc, repr(e)))
                    print(dotconnect(sl, eidc))
                    return

                labels[submenu] = label
                print(dotlabel(submenu, label))
                print(dotconnect(sl, submenu))

                await recurse(session,sub_tree,submenu,depth=depth - 1)
            except Exception as e:
                eidc = combine(combine(sl, 'ex'), i)
                print(dotlabel(eidc, repr(e)))
                print(dotconnect(sl, eidc))
        actions.append(action(i, entry))
    await asyncio.wait(actions)

async def amain(depth=3, vertical=False):
    async with aiohttp.ClientSession() as session:
        root = await rg(session)
        print("strict digraph {")
        if not vertical:
            print("rankdir=LR;")
        await recurse(session, root['Menu'], 'root', depth=depth)
        print("}")

def main(depth=3, vertical=False):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain(depth=depth, vertical=vertical))
    loop.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--depth', type=int, default=3)
    parser.add_argument('-v', '--vertical', action='store_true', default=False)
    args = parser.parse_args()
    main(depth=args.depth, vertical=args.vertical)

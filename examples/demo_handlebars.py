import sys
sys.path.append('..')

from quickjs import JSRuntime, JSContext, JSError, JSEval


def demo_online():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.load('https://cdnjs.cloudflare.com/ajax/libs/handlebars.js/4.7.8/handlebars.min.js')

    Handlebars = ctx['Handlebars']

    source = (
        "<p>Hello, my name is {{name}}. I am from {{hometown}}. I have "
        "{{kids.length}} kids:</p>"
        "<ul>{{#kids}}<li>{{name}} is {{age}}</li>{{/kids}}</ul>"
    )

    template = Handlebars.compile(source)

    data = {
        "name": "Alan",
        "hometown": "Somewhere, TX",
        "kids": [
            {"name": "Jimmy", "age": "12"},
            {"name": "Sally", "age": "4"},
        ]
    }

    result = template(data)
    print(str(result))


def demo_offline():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.load('node_modules/handlebars/dist/handlebars.min.js')

    Handlebars = ctx['Handlebars']

    source = (
        "<p>Hello, my name is {{name}}. I am from {{hometown}}. I have "
        "{{kids.length}} kids:</p>"
        "<ul>{{#kids}}<li>{{name}} is {{age}}</li>{{/kids}}</ul>"
    )

    template = Handlebars.compile(source)

    data = {
        "name": "Alan",
        "hometown": "Somewhere, TX",
        "kids": [
            {"name": "Jimmy", "age": "12"},
            {"name": "Sally", "age": "4"},
        ]
    }

    result = template(data)
    print(str(result))


if __name__ == '__main__':
    demo_online()
    demo_offline()

from flask import Flask, redirect, url_for, render_template

website = Flask(__name__)

@website.route('/')
def home_page():
    return render_template("home_page.html")

@website.route('/budget-organizer-<name>')
def budget_page(name):
    return render_template("budget_page.html")

# @app.route("/<name>")
# def home(name):
#     return render_template("home_page.html", content=["tim", "joe", "bill"])

if __name__ == "__main__":
    website.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Product, Order
import threading
from datetime import datetime, timezone
import time


app = Flask(__name__)
app.config["SECRET_KEY"] = "to_va47rishhh4891v"

engine = create_engine("sqlite:///tovarish.db", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()


def status_update(order_id):
    time.sleep(120)
    new_db = Session()
    order = new_db.query(Order).filter_by(id=order_id).first()
    if order and order.status == "В пути":
        order.status = "Доставлен"
        new_db.commit()
    new_db.close()


@app.route("/")
def main():
    return render_template("main.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password1 = request.form["password1"]
        password2 = request.form["password2"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        birth_date = request.form["birth_date"]

        if password1 != password2:
            return render_template("register.html", error="Пароли не совпадают")

        if db.query(User).filter_by(username=username).first():
            return render_template("register.html", error="Пользователь с таким логином уже существует")

        user = User(username=username, password=password1, first_name=first_name, last_name=last_name,
                    birth_date=birth_date)
        db.add(user)
        db.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = db.query(User).filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("profile"))
        else:
            return render_template("login.html", error="Неверный логин или пароль")

    return render_template("login.html")


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_orders = db.query(Order).filter_by(user_id=session["user_id"]).order_by(Order.created_at.desc()).all()
    return render_template("profile.html", orders=user_orders)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main"))


@app.route("/offers")
@app.route("/offers/<category>")
def offers(category=None):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if category and category != "all":
        product_list = db.query(Product).filter_by(category=category).all()
    else:
        product_list = db.query(Product).all()

    basket_count = db.query(Order).filter_by(user_id=session["user_id"], status="В корзине").count()

    return render_template("offers.html", products=product_list, category=category, cart_count=basket_count)


@app.route("/orders")
def orders():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_orders = db.query(Order).filter(Order.user_id == session["user_id"], Order.status != "В корзине").order_by(
        Order.created_at.desc()).all()
    return render_template("orders.html", orders=user_orders)


@app.route("/product_card/<int:product_id>")
def product_card(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    product_info = db.query(Product).filter_by(id=product_id).first()
    return render_template("product_card.html", product=product_info)


@app.route("/add_to_basket/<int:product_id>", methods=["POST"])
def add_to_basket(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    product_info = db.query(Product).filter_by(id=product_id).first()
    picked_size = request.form.get("size", "M")

    if product_info.stock <= 0:
        return redirect(url_for("offers"))

    new_order = Order(user_id=session["user_id"], product_id=product_info.id, product_name=product_info.name,
                      price=product_info.price, size=picked_size, status="В корзине")
    product_info.stock -= 1
    db.add(new_order)
    db.commit()

    return redirect(url_for("offers"))


@app.route("/basket")
def basket():
    if "user_id" not in session:
        return redirect(url_for("login"))

    basket_items = db.query(Order).filter_by(user_id=session["user_id"], status="В корзине").all()
    total_price = sum(item.price for item in basket_items)

    return render_template("basket.html", basket_items=basket_items, total=total_price)


@app.route("/remove_product/<int:order_id>")
def remove_product(order_id):
    order_to_remove = db.query(Order).filter_by(id=order_id).first()
    if order_to_remove and order_to_remove.user_id == session["user_id"]:
        product_info = db.query(Product).filter_by(id=order_to_remove.product_id).first()
        if product_info:
            product_info.stock += 1
        db.delete(order_to_remove)
        db.commit()

    return redirect(url_for("basket"))


@app.route("/buy")
def buy():
    if "user_id" not in session:
        return redirect(url_for("login"))

    basket_items = db.query(Order).filter_by(user_id=session["user_id"], status="В корзине").all()

    if not basket_items:
        return redirect(url_for("basket"))

    for item in basket_items:
        item.status = "В пути"
        item.created_at = datetime.now(timezone.utc)
        threading.Thread(target=status_update, args=(item.id,)).start()

    db.commit()

    return redirect(url_for("orders"))


if __name__ == "__main__":
    app.run(port=8080, host="127.0.0.1")
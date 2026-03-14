from django.urls import path
from .views import AddCartItem, CartByCustomer, CartDetail, CartItemDetail, CartItemList, CartListCreate

urlpatterns = [
    path('carts/', CartListCreate.as_view()),
    path('carts/by-customer/<int:customer_id>/', CartByCustomer.as_view()),
    path('carts/<int:cart_id>/', CartDetail.as_view()),
    path('carts/<int:cart_id>/items/', CartItemList.as_view()),
    path('cart-items/', AddCartItem.as_view()),
    path('cart-items/<int:item_id>/', CartItemDetail.as_view()),
]

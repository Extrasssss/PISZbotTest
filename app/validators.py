#import re
#from aiogram.types import Message


#def test_validator(message: Message):
#    if str(message) != 11:
#        raise ValueError('Неправильный номер')
#    return message()


#def validate_phonenumber(number):
#    r = re.compile('(\+7|8)\D*\d{3}\D*\d{3}\D*\d{2}\D*\d{2}')
#    if r.search(number):
#        return number()
#    else:
#        print('Введите корректный номер')

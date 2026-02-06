from fastapi import HTTPException, status
from DataAccess_Layer.dao.bank_detail_dao import BankDetailDAO
from http import HTTPStatus
import re

from DataAccess_Layer.dao.user_authentication import UserAuthDAO



class BankDetailService:
    def __init__(self, db=None):
        self.db = db
        self.dao = BankDetailDAO(self.db)
        self.user_dao = UserAuthDAO(self.db)

    def _is_valid_email(self, mail: str) -> bool:
        email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        return bool(re.match(email_regex, mail))

    def _is_strong_password(self, password: str) -> bool:
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):
            return False
        if not re.search(r"[a-z]", password):
            return False
        if not re.search(r"[0-9]", password):
            return False
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False
        return True
    def update_user_details(self, customer_id, request):
        try:
            existing = self.dao.checking_user_by_customer_id(customer_id)
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
            self._is_valid_email(request.mail)
            self._is_strong_password(request.password)
            user = self.user_dao.update_user_details(customer_id, request)
            return user
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        
    def admin_update_user_details(self, customer_id, request):
        try:
            existing = self.user_dao.checking_user_by_customer_id(customer_id)
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
            self._is_valid_email(request.mail)
            self._is_strong_password(request.password)
            user = self.dao.admin_update_user_details(customer_id, request)
            return user
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    def add_fiat_balance(self, tenant_id, customer_id, fiat_balance):
        try:
            user = self.dao.get_user_by_customer_id_and_tenant_id(customer_id, tenant_id)
            if not user:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="User not found"
                )
            new_balance = self.dao.add_fiat_balance(tenant_id, customer_id, fiat_balance)
            return new_balance
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
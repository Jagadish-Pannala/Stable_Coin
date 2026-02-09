from fastapi import HTTPException, status
from DataAccess_Layer.dao.bank_detail_dao import BankDetailDAO
from http import HTTPStatus
import re

from DataAccess_Layer.dao.user_authentication import UserAuthDAO
from utils.web3_client import Web3Client



class BankDetailService:
    def __init__(self, db=None):
        self.db = db
        self.web3 = Web3Client().w3
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
            existing = self.dao.get_user_by_customer_id(customer_id)
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )
            self._is_valid_email(request.mail)
            self._is_strong_password(request.password)
            user = self.dao.update_user_details(customer_id, request)
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
    def create_payee(self, customer_id, request):
        try:
            user = self.dao.get_user_by_customer_id(customer_id)
            if not user:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="User not found"
                )
            if not self.web3.is_address(request.wallet_address):
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Invalid wallet address"
                )
            existing_payee = self.dao.get_payee_by_wallet_address_and_user_id(request.wallet_address, user.id)
            if existing_payee:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Payee with this wallet address already exists"
                )
            payee_id = self.dao.create_payee(user.id, request)
            return payee_id.id
        except HTTPException as he: 
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    def get_payees(self, customer_id):
        try:
            user = self.dao.get_user_by_customer_id(customer_id)
            if not user:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="User not found"
                )
            print("User found:", user.id)
            payees = self.dao.get_payees(user.id)
            return payees
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    def delete_payee(self, customer_id, payee_id):
        try:
            user = self.dao.get_user_by_customer_id(customer_id)
            if not user:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="User not found"
                )
            payee = self.dao.get_payee_by_id(payee_id)
            if not payee or payee.customer_id != user.id:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Payee not found"
                )
            self.dao.delete_payee(payee_id)
            return {"message": "Payee deleted successfully"}
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
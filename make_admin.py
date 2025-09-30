# make_admin.py
import bcrypt


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


admin_pw = "Admin123!"   # đổi nếu muốn
employee_pw = "User123!"

print("Admin hash:")
print(hash_password(admin_pw))
print("\nEmployee hash:")
print(hash_password(employee_pw))

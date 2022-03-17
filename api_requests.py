from typing import List
import requests
from requests.structures import CaseInsensitiveDict
from config import Config
from lxml import etree
from loguru import logger


class ApiRequest:
    """
    Class for sending requests to the Ispring API

    """
    def __init__(self, new_user):
        self.base_url = Config.base_url
        self.headers = CaseInsensitiveDict()
        self.headers["Host"] = Config.Host
        self.headers["X-Auth-Account-Url"] = Config.X_Auth_Account_Url
        self.headers["X-Auth-Email"] = Config.X_Auth_Email
        self.headers["X-Auth-Password"] = Config.X_Auth_Password
        self.new_user = new_user

    def api_requests(self) -> None:
        """
        Method for processing registration request on Ispring

        :return: None
        """

        self.add_user()

        courses_to_add = Config.default_course_ids
        self.add_user_to_courses(courses_to_add)

    def check_exist_user(self) -> None:
        """
        Method for checking the existence of a user, checks by login = self.new_user.email or phone=self.new_user.phone

        :raise UserAlreadyExistsException if exists user with the same login
        :raise PhoneAlreadyExistsException if exists user with the same phone

        :return: bool check result

        """
        logger.debug(f"Checking user exists, user_data = {self.new_user}")

        url = f"{self.base_url}/user"
        email = self.new_user.email
        resp = requests.get(url, headers=self.headers)
        logger.debug(f"Ispring Checking user exists response: status code={resp.status_code}, content={resp.content[0:150]}")

        if resp.status_code != 200:  # other bad response
            raise Exception(f"Request check_exist_user failed {resp.status_code}")

        resp_xml_content = resp.content
        tree = etree.XML(resp_xml_content)
        user_by_email = tree.xpath(
            f'/response/userProfile/fields/field[name = "EMAIL" and value = "{email}"]')
        if user_by_email:
            self.new_user.user_id = (tree.xpath(
                f".//userProfile[./fields/field/name[contains(text(), 'LOGIN')] and ./fields/field/value[contains(text(), '{email}')]]/userId"))[
                0].text
            logger.warning(f"User with login {email} already exists, user_id: {self.new_user.user_id}")
            raise Exception(f"User with email '{self.new_user.email}' already exists")
        logger.info(f"User with login '{email}' doesn't exist yet")

        is_phone_already_exists = tree.xpath(
            f'/response/userProfile/fields/field[name = "PHONE" and value = "{self.new_user.phone}"]')
        if is_phone_already_exists:
            raise Exception(f"User with phone '{self.new_user.phone}' already exists")

    def add_user(self) -> bool:
        """
        Method for adding a new user to Ispring.
        raise BadUserIdException if Ispring not returned user_id

        :return: bool success
        """
        logger.debug(f"Trying to create a new user, user_data = {self.new_user}")

        url = f"{self.base_url}/user"

        self.headers["X-email"] = self.new_user.email
        resp = requests.post(url=url, headers=self.headers)

        logger.debug(f"Ispring create user response: status code={resp.status_code}, content={resp.content}")

        if resp.status_code == 409:  # other bad response
            logger.error(f"Failed to create user")
            self.new_user.user_id = resp_xml_content.split()[-1]
            raise Exception(f"User with login {self.new_user.email} already exists, user ID is {self.new_user.user_id}")

        if resp.status_code != 201:  # other bad response
            logger.error(f"Failed to create user")
            raise Exception(f"Request add_user failed {resp.status_code}")

        resp_xml_content = resp.content
        try:
            # the last or the only one data in response content is user_id
            self.new_user.user_id = resp_xml_content.split()[-1]
            logger.info(f"Add new user successful. User_id: {self.new_user.user_id}, user data: {self.new_user}")
            self.update_user_info()
            return True
        except Exception as ex:
            logger.error(f"Error get user_id from response {ex} XML content is {resp_xml_content}")
            return False

    def update_user_info(self):
        url = f"{self.base_url}/user/{self.new_user.user_id}"
        self.headers["X-Fields-Xml"] = f"<fields><first_name>{self.new_user.name}</first_name><last_name>{self.new_user.surname}</last_name><USER_FIELD_xPH1D>{self.new_user.phone}</USER_FIELD_xPH1D></fields>"
        resp = requests.post(url=url, headers=self.headers)

        if resp.status_code != 200:  # other bad response
            logger.error("Failed to update user")
            raise Exception(f"Request add_user failed {resp.status_code}")
        else:
            logger.info("User info updated correctly")

    def check_exist_course_user(self, course_id: str) -> bool:
        """
        Checks if the user has a course by course_id.
        raise CheckExistCourseException if check failed.

        :param course_id: string, id of a course in Ispring
        :return: bool success
        """
        logger.debug(f"Check user {self.new_user.user_id} for the purpose of the course {course_id}")
        url = f"{self.base_url}/enrollment"
        resp = requests.get(url, headers=self.headers)

        logger.debug(f"Ispring check_exist_course_user response: status code={resp.status_code}, content={resp.content}")
        if resp.status_code != 200:  # other bad response
            logger.error(f"Failed to check enrollment for user: {self.new_user.user_id} for course_id: {course_id}")
            raise Exception(f"Request check_exist_enrollment_user failed {resp.status_code}")

        resp_xml_content = resp.content
        tree = etree.XML(resp_xml_content)
        user_course_found = tree.xpath(
            f'/response/enrollment[./courseId="{course_id}" and ./learnerId="{self.new_user.user_id}"]')
        if user_course_found:
            logger.warning(f"User {self.new_user.user_id} already in list of learners on course {course_id}")
            return True
        logger.debug(f"User {self.new_user.user_id} has not yet been assigned a course {course_id}")
        return False

    def add_user_to_courses(self, courses: List[str]) -> bool:
        """
        Enroll the user to a courses.
        raise AddUserCourseException on failure.

        :param courses: list of courses id of a courses in Ispring
        :return: bool success
        """
        if not courses:
            logger.warning('add_user_to_courses method passed an empty list of courses')
            return False

        logger.debug(f"Trying to add user {self.new_user.user_id} on courses {courses}")
        url = f"{self.base_url}/enrollment"

        files = {
            'learnerIds[id]': (None, f'{self.new_user.user_id}')
        }
        for index, course_id in enumerate(courses):
            files[f'courseIds[id][{index}]'] = (None, course_id)

        resp = requests.post(url=url, headers=self.headers, files=files)

        logger.debug(f"Ispring add user to courses response: status code={resp.status_code}, content={resp.content}")
        if resp.status_code != 201:
            logger.debug(f"Error add user {self.new_user.user_id} for courses {courses}")
            raise Exception(f"Request add_user_to_enrollment failed {resp.status_code}")

        logger.info(f"Add user {self.new_user.user_id} on courses {courses} successful. resp.content:{resp.content},"
                    f" resp.text={resp.text}")
        return True

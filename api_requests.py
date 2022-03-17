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

        if self.add_user():
            try:
                self.update_user_info()
            except Exception as ex:
                logger.error(f"Error update_user_id: {ex}")
                return False

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
            return True
        except Exception as ex:
            logger.error(f"Error get user_id from response {ex} XML content is {resp_xml_content}")
            return False

    def update_user_info(self):
        url = f"{self.base_url}/user/{self.new_user.user_id}"
        self.headers.popitem()
        self.headers["X-Fields-Xml"] = etree.XML(f"<fields><first_name>{self.new_user.name}</first_name><last_name>{self.new_user.surname}</last_name><USER_FIELD_xPH1D>{self.new_user.phone}</USER_FIELD_xPH1D></fields>")
        resp = requests.post(url=url, headers=self.headers)

        if resp.status_code != 200:  # other bad response
            logger.error("Failed to update user")
            raise Exception(f"Request add_user failed {resp.status_code}")
        else:
            logger.info("User info updated correctly, trying to make enroll to course")
            self.add_user_to_courses(Config.default_course_ids)

    def add_user_to_courses(self, courses:List[int]) -> bool:
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

        self.headers.popitem()
        self.headers["X-Users"] = self.new_user.user_id

        for course in courses:
            url = f"{self.base_url}/content/{course}/invitation"

            resp = requests.post(url=url, headers=self.headers)

            logger.debug(f"Ispring add user to courses response: status code={resp.status_code}, content={resp.content}")
            if resp.status_code != 201:
                logger.debug(f"Error add user {self.new_user.user_id} for courses {courses}")
                raise Exception(f"Request add_user_to_enrollment failed {resp.status_code}")

            logger.info(f"Add user {self.new_user.user_id} on courses {courses} successful. resp.content:{resp.content},"
                        f" resp.text={resp.text}")
        return True

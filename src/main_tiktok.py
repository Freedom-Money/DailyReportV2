from datetime import datetime
import tiktok_utils
import sender.weixin_sender as weixin_sender
import os
import config
import pickle
import parse_yuque_config
import sender.email_sender as email_sender
import pandas as pd


def send_report(subject: str, body: str, file_path: str):
    """发送消息

    Args:
        subject (str): _description_
        body (str): _description_
        file_path (str): _description_
    """
    # 发送微信
    wxpusher_token = config.user_config['wxpusher_token']
    wechat_uid = os.environ['WECHAT_UID']
    if (wechat_uid != None and wechat_uid != ""):
        weixin_sender.send(body, subject, wxpusher_token, wechat_uid)
    # 发送邮件
    receive_email = os.environ['RECEIVE_EMAIL']
    if (receive_email != None and receive_email != ""):
        if receive_email.find(",") > 0:
            receive_emails = receive_email.split(",")
            for item in receive_emails:
                email_sender.send(
                    os.environ['SEND_EMAIL'], os.environ['SEND_EMAIL_PASSWORD'], item, body, file_path)
        else:
            email_sender.send(
                os.environ['SEND_EMAIL'], os.environ['SEND_EMAIL_PASSWORD'], receive_email, body, file_path)


def write_to_excel(data: list, file_path: str):
    """保存数据到excel

    Args:
        data (list): 数据
        file_path (str): 文件路径
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        tmp_list = []
        for item in data:
            tmp_list.append([item.number, item.operater, item.uid, item.deviceId, item.video_change, "", item.fans_change,
                            item.nick_name, item.fans_count, item.follow_count,
                            item.like_count, item.video_count, 
                            item.follow_change, item.like_change,  item.remarks])
        df = pd.DataFrame(tmp_list)
        df.columns = ['序号', '名字', '账号名', '机号', '今日视频量', '今日浏览量', '今日增粉量', 
                      '昵称', '粉丝数', '关注数', 
                      '点赞数', '视频数', 
                      '今日关注变化', '今日点赞变化',  '备注']
        df = df.sort_values(by='序号', ascending=True)
        df.to_excel(file_path, index=False)
    except Exception as err:
        print("保存文件错误")
        print(err)


if __name__ == "__main__":
    try:
        # 读取项目配置
        tiktok_cookie = config.user_config['tiktok_cookie']
        # 读取环境变量配置
        yuque_doc_url = os.environ['YUQUE_DOC_URL']

        accounts = set()
        try:
            accounts = parse_yuque_config.parse_yuque_config(yuque_doc_url)
        except Exception as err:
            print("获取语雀配置失败")
            send_report("TikTok日报 - 运行异常", "读取语雀配置错误，请检查配置", None)
            raise err
        current_date = datetime.now().strftime("%Y%m%d")
        doc_uid = "Tiktok日报_{}".format(current_date)
        daily_data_file = os.path.abspath(f'{doc_uid}.pkl')
        data = None
        if os.path.exists(daily_data_file):
            # 打开保存对象的文件，使用二进制读取模式
            with open(daily_data_file, 'rb') as file:
                data = pickle.load(file)
        else:
            print(f"The file {daily_data_file} does not exist.")
        users = []
        result = ""
        for item in accounts:
            info = tiktok_utils.get_account_info(item, tiktok_cookie)
            if info == None:
                print("获取用户信息失败")
                result += f'\n用户信息丢失:{item.uid}({item.operater} - {item.number})'
            else:
                users.append(info)
                yesterday = None
                try:
                    if data is not None:
                        for tmpItem in data:
                            if tmpItem.username == info.username:
                                yesterday = tmpItem
                                break
                except Exception as err:
                    print('获取对比信息错误')
                    print(err)

                if yesterday != None:
                    info.set_yesterday(int(yesterday.follow_count), int(yesterday.fans_count),
                                       int(yesterday.like_count), int(yesterday.video_count))
                result += info.toString()

        # 保存文件
        with open(daily_data_file, 'wb') as file:
            pickle.dump(users, file)
        tmp_excel = f'{doc_uid}.xlsx'
        write_to_excel(users, tmp_excel)
        send_report("TikTok日报", result, tmp_excel)

        # 删除excel文件
        if os.path.exists(tmp_excel):
            os.remove(tmp_excel)

    except Exception as err:
        print("运行错误")
        print(err)

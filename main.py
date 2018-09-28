import paramiko
import re
import pickle
import sys
import json
import smtplib
from email import encoders
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr


def is_cidr(data):  # "IPv4过滤函数"
    cidr = re.compile(
        '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}$')  # ipv4正则表达式
    return cidr.match(data)


def del_private(data):
    private = re.compile('^(10|14).*')
    if not private.match(data):
        return data


def get_info(device, account, cmd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=device, username=account[0], password=account[1])
    stdin, stdout, stderr = client.exec_command(cmd)
    result = []
    for line in stdout:
        line = list(filter(is_cidr, line.split()))
        result.extend(line)
    client.close()
    return result


def diff(now, history):

    try:
        with open(history, 'rb') as i:
            old = set(pickle.load(i))
    except:
        IndexError
        old = set()

    with open(history, 'wb') as i:
        pickle.dump(now, i)

    new = set(now)
    add = new - old or None  # 新增差量
    remove = old - new or None
    return (add, remove)


def to_str(args):
    return str('\n'.join(sorted(args)))


def format(add, remove):
    if add and remove:
        add = to_str(add)
        remove = to_str(remove)
        context = '新增\n%s\n\n删除\n%s' % (add, remove)
    elif not add and remove:
        remove = to_str(remove)
        context = '删除\n%s' % (remove)
    elif add and not remove:
        add = to_str(add)
        context = '新增\n%s' % (add)
    else:
        context = None
    return context


def _format_addr(s):
    name, addr = parseaddr(s)
    return formataddr((Header(name).encode(), addr))


def let_them_know(header, context):
    print(context)
    email = '%s/email.json' % sys.path[0]
    with open(email, 'r', encoding='utf-8') as f:
        email_info = json.load(f)
    to_addr = email_info.get('to_addr')
    # 生成收件人列表
    email_list = ','.join(_format_addr('%s <%s>' % (k, v))
                          for k, v in to_addr.items())
    # 填写邮件内容
    msg = MIMEText(context, 'plain', 'utf-8')
    msg['From'] = _format_addr('天津网管监控 <%s>' % email_info['from_addr'])
    msg['To'] = email_list
    msg['Subject'] = Header(header).encode()
    # 发送邮件
    server = smtplib.SMTP(email_info['smtp_server'], 25)
    server.login(email_info['from_addr'], email_info['passwd'])
    server.sendmail(email_info['from_addr'], to_addr.values(), msg.as_string())
    server.quit()


if __name__ == '__main__':
    GR3 = '220.113.135.52'
    cmd = 'show route receive-protocol bgp 14.197.247.112'
    account = ('xiayu', 'tjgwbn123')
    iplist = list(filter(del_private, get_info(GR3, account, cmd)))
    add, remove = diff(iplist, 'internal.txt')
    result = format(add, remove)
    if result:
        let_them_know('内网地址组更新', result)
    else:
        print('meiyou')

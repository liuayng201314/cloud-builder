#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rclone.conf配置文件pass字段解密工具

参考rclone源码中的obscure算法实现：
- fs/config/obscure/obscure.go
- 使用AES-CTR模式加密
- 固定密钥用于加密/解密
"""

import base64
import sys
from typing import Dict, Any, Optional
from Crypto.Cipher import AES


# rclone obscure算法使用的固定密钥
CRYPT_KEY = bytes([
    0x9c, 0x93, 0x5b, 0x48, 0x73, 0x0a, 0x55, 0x4d,
    0x6b, 0xfd, 0x7c, 0x63, 0xc8, 0x86, 0xa9, 0x2b,
    0xd3, 0x90, 0x19, 0x8e, 0xb8, 0x12, 0x8a, 0xfb,
    0xf4, 0xde, 0x16, 0x2b, 0x8b, 0x95, 0xf6, 0x38,
])


def reveal(obscured_value: str) -> str:
    """
    解密rclone obscure算法加密的值
    
    参考Go实现：fs/config/obscure/obscure.go
    - 使用base64.RawURLEncoding（不使用padding）
    - 使用AES-CTR模式加密
    - IV是16字节，放在密文前面
    
    Args:
        obscured_value: base64.RawURLEncoding编码的加密字符串
        
    Returns:
        解密后的原始字符串
        
    Raises:
        ValueError: 如果输入格式不正确或解密失败
    """
    try:
        # base64.RawURLEncoding解码（不使用padding）
        # Python的urlsafe_b64decode可以处理没有padding的情况
        # 但为了与Go的RawURLEncoding完全一致，需要手动处理
        # Go的RawURLEncoding不使用padding，Python需要添加padding才能解码
        padding_len = len(obscured_value) % 4
        if padding_len:
            padded_value = obscured_value + '=' * (4 - padding_len)
        else:
            padded_value = obscured_value
        ciphertext = base64.urlsafe_b64decode(padded_value)
    except Exception as e:
        raise ValueError(f"base64解码失败，输入可能不是obscure加密的值: {e}")
    
    # 检查长度（至少需要16字节的IV）
    if len(ciphertext) < AES.block_size:
        raise ValueError("输入太短，不是有效的obscure加密值")
    
    # 前16字节是IV（初始化向量），后面是密文
    iv = ciphertext[:AES.block_size]
    encrypted_data = ciphertext[AES.block_size:]
    
    # Go的cipher.NewCTR实现：
    # 根据Go标准库crypto/cipher/ctr.go的实现：
    # - 使用整个16字节IV作为初始counter block
    # - 每次递增后8字节（big-endian，有进位处理）
    # - 第一个counter block = IV（整个16字节）
    # - 后续counter block = IV的前8字节（nonce，保持不变）|| (IV的后8字节 + block_index)
    # 手动实现CTR模式以完全匹配Go的行为
    cipher_block = AES.new(CRYPT_KEY, AES.MODE_ECB)
    decrypted = bytearray()
    block_size = AES.block_size
    
    # nonce是IV的前8字节（保持不变）
    nonce = iv[:8]
    # 初始counter值是IV的后8字节（big-endian）
    initial_counter = int.from_bytes(iv[8:], 'big')
    
    for i in range(0, len(encrypted_data), block_size):
        # 构造counter block: nonce(8字节) || (initial_counter + block_index)(8字节，big-endian)
        block_index = i // block_size
        # 计算counter值（处理溢出，但Go的实现会处理进位）
        counter_value = (initial_counter + block_index) & 0xFFFFFFFFFFFFFFFF
        counter_bytes = counter_value.to_bytes(8, 'big')
        counter_block = nonce + counter_bytes
        
        # 加密counter block得到keystream
        keystream = cipher_block.encrypt(counter_block)
        
        # XOR解密（CTR模式下加密和解密是同一个操作）
        block = encrypted_data[i:i+block_size]
        decrypted_block = bytes(a ^ b for a, b in zip(block, keystream[:len(block)]))
        decrypted.extend(decrypted_block)
    
    decrypted = bytes(decrypted)
    
    return decrypted.decode('utf-8', errors='ignore')


def get_remote_config(config_path: str = None, remote_name: str = None) -> Dict[str, Any]:
    """
    从rclone.conf配置文件中获取指定远程的配置信息（返回字典）
    
    完全按照rclone的配置文件查找逻辑（参考fs/config/config.go的makeConfigPath函数）：
    1. 环境变量 RCLONE_CONFIG
    2. <rclone_exe_dir>/rclone.conf (可执行文件所在目录)
    3. Windows: %APPDATA%/rclone/rclone.conf
    4. $XDG_CONFIG_HOME/rclone/rclone.conf (所有系统，包括Windows)
    5. ~/.config/rclone/rclone.conf
    6. ~/.rclone.conf (legacy)
    7. .rclone.conf (当前工作目录，最后手段)
    
    Args:
        config_path: rclone.conf配置文件路径，如果为None则尝试自动查找
        remote_name: 远程名称，必须指定
        
    Returns:
        包含配置信息的字典，如果未找到则返回None
        
    Raises:
        ValueError: 如果remote_name未指定或配置不存在
    """
    import os
    import configparser
    from typing import Dict, Any
    
    if not remote_name:
        raise ValueError("remote_name必须指定")
    
    # 查找配置文件（复用decrypt_pass_from_config的逻辑）
    if config_path is None:
        # 1. 首先检查环境变量 RCLONE_CONFIG
        rclone_config_env = os.getenv('RCLONE_CONFIG')
        if rclone_config_env and os.path.exists(rclone_config_env):
            config_path = rclone_config_env
        else:
            # 按rclone的查找顺序查找配置文件
            possible_paths = []
            
            # 2. <rclone_exe_dir>/rclone.conf
            try:
                cwd_rclone_conf = os.path.join(os.getcwd(), 'rclone.conf')
                if os.path.exists(cwd_rclone_conf):
                    possible_paths.append(cwd_rclone_conf)
            except:
                pass
            
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                exe_config = os.path.join(script_dir, 'rclone.conf')
                if os.path.exists(exe_config):
                    possible_paths.append(exe_config)
            except:
                pass
            
            try:
                exe_dir = os.path.dirname(os.path.abspath(sys.executable))
                exe_config = os.path.join(exe_dir, 'rclone.conf')
                if os.path.exists(exe_config):
                    possible_paths.append(exe_config)
            except:
                pass
            
            # 3. Windows: %APPDATA%/rclone/rclone.conf
            if sys.platform == 'win32':
                appdata = os.getenv('APPDATA')
                if appdata:
                    appdata_config = os.path.join(appdata, 'rclone', 'rclone.conf')
                    if os.path.exists(appdata_config):
                        possible_paths.append(appdata_config)
            
            # 4. $XDG_CONFIG_HOME/rclone/rclone.conf (所有系统，包括Windows)
            xdg_config = os.getenv('XDG_CONFIG_HOME')
            if xdg_config:
                xdg_config_path = os.path.join(xdg_config, 'rclone', 'rclone.conf')
                if os.path.exists(xdg_config_path):
                    possible_paths.append(xdg_config_path)
            
            # 5. ~/.config/rclone/rclone.conf
            try:
                home = os.path.expanduser('~')
                if home:
                    dot_config = os.path.join(home, '.config', 'rclone', 'rclone.conf')
                    if os.path.exists(dot_config):
                        possible_paths.append(dot_config)
            except:
                pass
            
            # 6. ~/.rclone.conf (legacy)
            try:
                home = os.path.expanduser('~')
                if home:
                    old_home_config = os.path.join(home, '.rclone.conf')
                    if os.path.exists(old_home_config):
                        possible_paths.append(old_home_config)
            except:
                pass
            
            # 7. .rclone.conf (当前工作目录，最后手段)
            try:
                cwd_config = os.path.join(os.getcwd(), '.rclone.conf')
                if os.path.exists(cwd_config):
                    possible_paths.append(cwd_config)
            except:
                pass
            
            # 查找存在的配置文件（按优先级）
            config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            
            if config_path is None:
                raise ValueError("未找到rclone.conf配置文件")
    
    if not os.path.exists(config_path):
        raise ValueError(f"配置文件不存在: {config_path}")
    
    # 读取配置文件
    config = configparser.ConfigParser()
    try:
        config.read(config_path, encoding='utf-8')
    except Exception as e:
        raise ValueError(f"无法读取配置文件: {e}")
    
    # 检查指定的section是否存在
    if not config.has_section(remote_name):
        raise ValueError(f"未找到远程配置: {remote_name}")
    
    # 获取配置信息并解密pass字段
    config_dict = {}
    for key, value in config[remote_name].items():
        if key == 'pass':
            # 解密pass字段
            try:
                config_dict[key] = reveal(value)
            except Exception as e:
                raise ValueError(f"pass字段解密失败: {e}")
        else:
            config_dict[key] = value
    
    return config_dict


def decrypt_pass_from_config(config_path: str = None, remote_name: str = None):
    """
    从rclone.conf配置文件中解密pass字段并输出所有配置属性
    
    完全按照rclone的配置文件查找逻辑（参考fs/config/config.go的makeConfigPath函数）：
    1. 环境变量 RCLONE_CONFIG
    2. <rclone_exe_dir>/rclone.conf (可执行文件所在目录)
    3. Windows: %APPDATA%/rclone/rclone.conf
    4. $XDG_CONFIG_HOME/rclone/rclone.conf (所有系统，包括Windows)
    5. ~/.config/rclone/rclone.conf
    6. ~/.rclone.conf (legacy)
    7. .rclone.conf (当前工作目录，最后手段)
    
    Args:
        config_path: rclone.conf配置文件路径，如果为None则尝试自动查找
        remote_name: 远程名称，如果为None则解密所有远程的配置
    """
    import os
    import configparser
    
    # 查找配置文件
    if config_path is None:
        # 1. 首先检查环境变量 RCLONE_CONFIG
        rclone_config_env = os.getenv('RCLONE_CONFIG')
        if rclone_config_env and os.path.exists(rclone_config_env):
            config_path = rclone_config_env
        else:
            # 按rclone的查找顺序查找配置文件
            possible_paths = []
            
            # 2. <rclone_exe_dir>/rclone.conf
            # rclone会查找可执行文件所在目录中的rclone.conf（便携模式）
            # 对于Python脚本，我们查找以下位置：
            # - 当前工作目录中的rclone.conf（便携模式，不带点）
            # - Python脚本所在目录中的rclone.conf
            # - sys.executable所在目录中的rclone.conf（Python解释器目录）
            try:
                # 当前工作目录中的rclone.conf（便携模式）
                cwd_rclone_conf = os.path.join(os.getcwd(), 'rclone.conf')
                if os.path.exists(cwd_rclone_conf):
                    possible_paths.append(cwd_rclone_conf)
            except:
                pass
            
            try:
                # Python脚本所在目录
                script_dir = os.path.dirname(os.path.abspath(__file__))
                exe_config = os.path.join(script_dir, 'rclone.conf')
                if os.path.exists(exe_config):
                    possible_paths.append(exe_config)
            except:
                pass
            
            try:
                # sys.executable所在目录（Python解释器目录）
                exe_dir = os.path.dirname(os.path.abspath(sys.executable))
                exe_config = os.path.join(exe_dir, 'rclone.conf')
                if os.path.exists(exe_config):
                    possible_paths.append(exe_config)
            except:
                pass
            
            # 3. Windows: %APPDATA%/rclone/rclone.conf
            if sys.platform == 'win32':
                appdata = os.getenv('APPDATA')
                if appdata:
                    appdata_config = os.path.join(appdata, 'rclone', 'rclone.conf')
                    if os.path.exists(appdata_config):
                        possible_paths.append(appdata_config)
            
            # 4. $XDG_CONFIG_HOME/rclone/rclone.conf (所有系统，包括Windows)
            xdg_config = os.getenv('XDG_CONFIG_HOME')
            if xdg_config:
                xdg_config_path = os.path.join(xdg_config, 'rclone', 'rclone.conf')
                if os.path.exists(xdg_config_path):
                    possible_paths.append(xdg_config_path)
            
            # 5. ~/.config/rclone/rclone.conf
            try:
                home = os.path.expanduser('~')
                if home:
                    dot_config = os.path.join(home, '.config', 'rclone', 'rclone.conf')
                    if os.path.exists(dot_config):
                        possible_paths.append(dot_config)
            except:
                pass
            
            # 6. ~/.rclone.conf (legacy)
            try:
                home = os.path.expanduser('~')
                if home:
                    old_home_config = os.path.join(home, '.rclone.conf')
                    if os.path.exists(old_home_config):
                        possible_paths.append(old_home_config)
            except:
                pass
            
            # 7. .rclone.conf (当前工作目录，最后手段，legacy隐藏文件名)
            try:
                cwd_config = os.path.join(os.getcwd(), '.rclone.conf')
                if os.path.exists(cwd_config):
                    possible_paths.append(cwd_config)
            except:
                pass
            
            # 查找存在的配置文件（按优先级）
            config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            
            if config_path is None:
                print("错误: 未找到rclone.conf配置文件")
                print("查找顺序（完全按照rclone的查找逻辑）:")
                print("  1. 环境变量 RCLONE_CONFIG")
                print("  2. <可执行文件目录>/rclone.conf")
                print("     - 当前工作目录/rclone.conf (便携模式)")
                print("     - Python脚本目录/rclone.conf")
                print("     - Python解释器目录/rclone.conf")
                if sys.platform == 'win32':
                    print("  3. %APPDATA%/rclone/rclone.conf")
                print("  4. $XDG_CONFIG_HOME/rclone/rclone.conf (所有系统)")
                print("  5. ~/.config/rclone/rclone.conf")
                print("  6. ~/.rclone.conf (legacy)")
                print("  7. ./.rclone.conf (当前工作目录，最后手段)")
                print("\n请使用 --config 参数指定配置文件路径")
                return
    
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        return
    
    # 读取配置文件
    config = configparser.ConfigParser()
    try:
        config.read(config_path, encoding='utf-8')
    except Exception as e:
        print(f"错误: 无法读取配置文件: {e}")
        return
    
    # 获取所有section或指定的section
    sections = [remote_name] if remote_name else config.sections()
    
    if not sections:
        print("配置文件为空或没有找到任何远程配置")
        return
    
    # 解密每个section的配置，输出所有属性
    for section in sections:
        if not config.has_section(section):
            print(f"警告: 未找到远程配置: {section}")
            continue
        
        print(f"[{section}]")
        
        # 输出所有配置项
        for key, value in config[section].items():
            # 如果是pass字段，尝试解密
            if key == 'pass':
                try:
                    decrypted_pass = reveal(value)
                    print(f"{key} = {decrypted_pass}")
                except Exception as e:
                    print(f"{key} = {value}  # 解密失败: {e}")
            else:
                # 其他字段直接输出
                print(f"{key} = {value}")
        
        print()


def main():
    """主函数
    rclone.conf配置文件内容：
[remote76]
type = sftp
host = 10.238.110.76
user = root
pass = UGMve60UljEIf0q0OMtSAWgN_fN55M2rDWM2QA
shell_type = unix

[route84]
type = sftp
user = ngcc
host = 10.234.157.84
pass = Mqb49ej4BSbWJG_8lKhC_4L5ha1wJk0866Kh0A
shell_type = unix
md5sum_command = md5sum
sha1sum_command = sha1sum
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='解密rclone.conf配置文件中的pass字段并输出所有配置属性',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 解密所有远程的配置（pass字段会解密，其他字段原样输出）
  python rclone_decrypt_pass.py
  
  # 解密指定远程的配置
  python rclone_decrypt_pass.py --remote myremote
  
  # 指定配置文件路径
  python rclone_decrypt_pass.py --config /path/to/rclone.conf
  
  # 直接解密一个obscure值
  python rclone_decrypt_pass.py --value "YmJiYmJiYmJiYmJiYmJiYp*gcEWbAw"
        """
    )
    
    parser.add_argument('--config', '-c', 
                       help='rclone.conf配置文件路径（默认自动查找）')
    parser.add_argument('--remote', '-r',
                       help='要解密的远程名称（默认解密所有远程）')
    parser.add_argument('--value', '-v',
                       help='直接解密一个obscure加密的值')
    
    args = parser.parse_args()
    
    if args.value:
        # 直接解密单个值
        try:
            decrypted = reveal(args.value)
            print(decrypted)
        except Exception as e:
            print(f"解密失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 从配置文件解密
        decrypt_pass_from_config(args.config, args.remote)


if __name__ == '__main__':
    main()


import os
import re
import random
import shutil
from typing import List, Tuple, Dict

class InvoiceAllocator:
    def __init__(self):
        self.invoices = []
        self.people = []
        self.allocations = {}
        self.folder_path = "."  # 默认当前目录
        self.lower_bound = 0.97  # 默认下限
        self.upper_bound = 1.03  # 默认上限
        
    def get_user_input(self):
        """获取用户输入的人名、额度和参数"""
        print("=== 发票分配系统 ===")
        
        # 获取人数
        while True:
            try:
                num_people = int(input("请输入分配人数: ").strip())
                if num_people <= 0:
                    print("人数必须为正整数！")
                    continue
                break
            except ValueError:
                print("请输入有效数字！")
        
        # 获取人名和额度
        print(f"\n请输入{num_people}个人名及对应的额度（格式：甲 200 乙 150 丙 360 ...）")
        
        while True:
            try:
                input_str = input("请输入: ").strip()
                parts = input_str.split()
                
                if len(parts) != num_people * 2:
                    print(f"输入格式错误！请确保输入{num_people}个人名和{num_people}个额度，共{num_people*2}个元素")
                    continue
                
                self.people = []
                allocations_temp = {}
                
                for i in range(0, num_people * 2, 2):
                    name = parts[i]
                    try:
                        amount = float(parts[i+1])
                        if amount <= 0:
                            print("额度必须为正数！")
                            raise ValueError
                    except ValueError:
                        print("额度必须是有效的数字！")
                        raise
                    
                    self.people.append(name)
                    allocations_temp[name] = amount
                
                self.allocations = allocations_temp
                print(f"\n输入成功！")
                for name, amount in self.allocations.items():
                    print(f"{name}: {amount}元")
                break
                
            except Exception as e:
                print("输入有误，请重新输入！")
                continue
        
        # 获取分配范围参数
        print("\n请输入分配范围参数（相对于额度的百分比）")
        while True:
            try:
                lower_input = input("下限（默认0.97，即97%）: ").strip()
                upper_input = input("上限（默认1.03，即103%）: ").strip()
                
                if lower_input:
                    self.lower_bound = float(lower_input)
                    if self.lower_bound <= 0 or self.lower_bound >= 1:
                        print("下限必须在0和1之间！")
                        continue
                
                if upper_input:
                    self.upper_bound = float(upper_input)
                    if self.upper_bound <= 1:
                        print("上限必须大于1！")
                        continue
                
                if self.lower_bound >= self.upper_bound:
                    print("下限必须小于上限！")
                    continue
                
                print(f"\n分配范围设置成功：{self.lower_bound*100}% - {self.upper_bound*100}%")
                break
                
            except ValueError:
                print("请输入有效数字！")
    
    def scan_invoices(self, folder_path="."):
        """扫描文件夹中的发票文件"""
        self.folder_path = folder_path
        print("正在扫描发票文件...")
        self.invoices = []
        
        # 支持多种文件扩展名
        pdf_pattern = re.compile(r'\.pdf$', re.IGNORECASE)
        
        for filename in os.listdir(folder_path):
            if pdf_pattern.search(filename):
                # 提取金额
                amount = self.extract_amount_from_filename(filename)
                if amount is not None:
                    self.invoices.append((filename, amount))
        
        print(f"找到 {len(self.invoices)} 张发票")
        
        if not self.invoices:
            print("警告：未找到任何发票文件！")
            return False
        
        # 显示发票统计信息
        total_amount = sum(amount for _, amount in self.invoices)
        print(f"发票总金额: {total_amount:.2f}元")
        
        # 检查总金额是否在合理范围内
        total_quota = sum(self.allocations.values())
        min_total = total_quota * self.lower_bound
        max_total = total_quota * self.upper_bound
        
        if total_amount < min_total:
            print(f"警告：发票总金额({total_amount:.2f}元)小于最低要求金额({min_total:.2f}元)")
            print("可能无法找到满足要求的分配方案")
        elif total_amount > max_total:
            print(f"警告：发票总金额({total_amount:.2f}元)超过最大允许金额({max_total:.2f}元)")
            print("将使用部分发票进行分配")
        
        return True
    
    def extract_amount_from_filename(self, filename: str) -> float:
        """从文件名中提取金额 - 修复版本"""
        # 移除文件扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 改进的正则表达式：匹配人名后的第一个金额，忽略括号内的数字
        # 模式：空格后跟数字（可能包含小数点），然后可能是空格和括号
        amount_pattern = re.compile(r'\s+(\d+\.?\d*)\s*(?:\(|\.pdf|$)')
        match = amount_pattern.search(name_without_ext)
        
        if match:
            try:
                amount = float(match.group(1))
                return amount
            except ValueError:
                pass
        
        # 备用方案：尝试匹配文件名中的任何金额（排除括号内的）
        # 先移除括号内容，再匹配金额
        name_without_brackets = re.sub(r'\([^)]*\)', '', name_without_ext)
        amount_pattern_fallback = re.compile(r'(\d+\.?\d*)')
        matches = amount_pattern_fallback.findall(name_without_brackets)
        
        if matches:
            try:
                # 取最大的数字作为金额（假设金额是最大的数字）
                amounts = [float(m) for m in matches]
                return max(amounts)
            except ValueError:
                pass
        
        print(f"警告：无法从文件名 '{filename}' 中提取金额")
        return None
    
    def calculate_score(self, actual, target):
        """计算分配得分：优先超额"""
        min_amount = target * self.lower_bound
        max_amount = target * self.upper_bound
        
        if actual < min_amount:
            # 低于下限，惩罚较大
            return (min_amount - actual) ** 2 * 10
        elif actual <= target:
            # 在目标值以下但在范围内，轻微惩罚
            return (target - actual) ** 2
        elif actual <= max_amount:
            # 在目标值以上但在范围内，奖励（负惩罚）
            # 使用较小的惩罚值，鼓励超额
            return (actual - target) ** 2 * 0.5
        else:
            # 超过上限，惩罚很大
            return (actual - max_amount) ** 2 * 100
    
    def find_optimal_allocation(self):
        """使用增强的最小偏差算法寻找最优分配方案"""
        print("\n正在计算最优分配方案...")
        print("这可能需要一些时间，请耐心等待...")
        
        # 使用增强的最小偏差算法
        return self.enhanced_min_deviation_allocation()
    
    def enhanced_min_deviation_allocation(self):
        """增强的最小偏差算法"""
        # 多次尝试，选择偏差最小的方案
        best_allocation = None
        best_amounts = None
        best_score = float('inf')
        
        # 根据发票数量和人数调整迭代次数
        if len(self.invoices) <= 20 and len(self.people) <= 4:
            num_iterations = 100
        elif len(self.invoices) <= 40 and len(self.people) <= 6:
            num_iterations = 50
        else:
            num_iterations = 30
        
        print(f"使用增强算法，进行 {num_iterations} 次迭代...")
        
        for iteration in range(num_iterations):
            if iteration % 10 == 0:
                print(f"已完成 {iteration}/{num_iterations} 次迭代...")
            
            allocation = {name: [] for name in self.allocations}
            amounts = {name: 0.0 for name in self.allocations}
            
            # 使用不同的初始策略
            if iteration % 3 == 0:
                # 策略1: 随机打乱发票
                shuffled_invoices = self.invoices.copy()
                random.shuffle(shuffled_invoices)
            elif iteration % 3 == 1:
                # 策略2: 按金额降序排列
                shuffled_invoices = sorted(self.invoices, key=lambda x: x[1], reverse=True)
            else:
                # 策略3: 按金额升序排列
                shuffled_invoices = sorted(self.invoices, key=lambda x: x[1])
            
            # 第一阶段：初始分配
            for filename, amount in shuffled_invoices:
                best_person = None
                best_score_local = float('inf')
                
                for name, quota in self.allocations.items():
                    min_amount = quota * self.lower_bound
                    max_amount = quota * self.upper_bound
                    
                    if amounts[name] + amount <= max_amount:
                        # 计算分配后的总得分
                        temp_amounts = amounts.copy()
                        temp_amounts[name] += amount
                        
                        score = 0
                        for n, q in self.allocations.items():
                            score += self.calculate_score(temp_amounts[n], q)
                        
                        if score < best_score_local:
                            best_score_local = score
                            best_person = name
            
                if best_person is not None:
                    allocation[best_person].append((filename, amount))
                    amounts[best_person] += amount
            
            # 第二阶段：局部优化
            improved = True
            local_improvements = 0
            max_local_iterations = min(100, len(self.invoices) * 2)
            
            while improved and local_improvements < max_local_iterations:
                improved = False
                local_improvements += 1
                
                # 尝试交换发票来优化
                for name1 in self.allocations:
                    for name2 in self.allocations:
                        if name1 == name2:
                            continue
                        
                        # 尝试交换两张发票
                        for i, (filename1, amount1) in enumerate(allocation[name1]):
                            for j, (filename2, amount2) in enumerate(allocation[name2]):
                                # 计算交换后的金额
                                new_amount1 = amounts[name1] - amount1 + amount2
                                new_amount2 = amounts[name2] - amount2 + amount1
                                
                                quota1 = self.allocations[name1]
                                quota2 = self.allocations[name2]
                                min_amount1 = quota1 * self.lower_bound
                                max_amount1 = quota1 * self.upper_bound
                                min_amount2 = quota2 * self.lower_bound
                                max_amount2 = quota2 * self.upper_bound
                                
                                # 检查是否满足约束
                                if (min_amount1 <= new_amount1 <= max_amount1 and 
                                    min_amount2 <= new_amount2 <= max_amount2):
                                    
                                    # 计算交换前后的得分
                                    old_score = (self.calculate_score(amounts[name1], quota1) + 
                                               self.calculate_score(amounts[name2], quota2))
                                    new_score = (self.calculate_score(new_amount1, quota1) + 
                                               self.calculate_score(new_amount2, quota2))
                                    
                                    if new_score < old_score:
                                        # 执行交换
                                        allocation[name1][i], allocation[name2][j] = (
                                            allocation[name2][j], allocation[name1][i])
                                        amounts[name1] = new_amount1
                                        amounts[name2] = new_amount2
                                        improved = True
                                        break
                            
                            if improved:
                                break
                        if improved:
                            break
                    if improved:
                        break
                
                # 如果没有交换改进，尝试移动发票
                if not improved:
                    for name1 in self.allocations:
                        for name2 in self.allocations:
                            if name1 == name2:
                                continue
                            
                            # 尝试将发票从name1移动到name2
                            for i, (filename, amount) in enumerate(allocation[name1]):
                                # 计算移动后的金额
                                new_amount1 = amounts[name1] - amount
                                new_amount2 = amounts[name2] + amount
                                
                                quota1 = self.allocations[name1]
                                quota2 = self.allocations[name2]
                                min_amount1 = quota1 * self.lower_bound
                                max_amount1 = quota1 * self.upper_bound
                                min_amount2 = quota2 * self.lower_bound
                                max_amount2 = quota2 * self.upper_bound
                                
                                # 检查是否满足约束
                                if (min_amount1 <= new_amount1 <= max_amount1 and 
                                    min_amount2 <= new_amount2 <= max_amount2):
                                    
                                    # 计算移动前后的得分
                                    old_score = (self.calculate_score(amounts[name1], quota1) + 
                                               self.calculate_score(amounts[name2], quota2))
                                    new_score = (self.calculate_score(new_amount1, quota1) + 
                                               self.calculate_score(new_amount2, quota2))
                                    
                                    if new_score < old_score:
                                        # 执行移动
                                        allocation[name2].append(allocation[name1].pop(i))
                                        amounts[name1] = new_amount1
                                        amounts[name2] = new_amount2
                                        improved = True
                                        break
                            
                            if improved:
                                break
                        if improved:
                            break
            
            # 计算当前方案的得分
            score = 0
            valid = True
            for name, quota in self.allocations.items():
                min_amount = quota * self.lower_bound
                max_amount = quota * self.upper_bound
                
                if amounts[name] < min_amount or amounts[name] > max_amount:
                    valid = False
                    break
                
                score += self.calculate_score(amounts[name], quota)
            
            if valid and score < best_score:
                best_score = score
                best_allocation = allocation.copy()
                best_amounts = amounts.copy()
                print(f"发现更好方案，得分: {best_score:.4f}")
        
        if best_allocation:
            print(f"找到最优方案，最终得分: {best_score:.4f}")
            return best_allocation, best_amounts
        else:
            # 如果没有完全有效的方案，返回最后一次尝试的结果
            print("未找到完全符合要求的方案，返回最佳近似方案")
            return allocation, amounts
    
    def display_solution(self, allocation, amounts):
        """显示解决方案"""
        print("\n" + "="*60)
        print("最优分配方案")
        print("="*60)
        
        total_score = 0
        all_valid = True
        total_used = 0
        total_invoices_used = 0
        
        # 计算超额人数
        excess_count = 0
        for name in self.people:
            target = self.allocations[name]
            actual = amounts[name]
            if actual > target:
                excess_count += 1
        
        for name in self.people:
            target = self.allocations[name]
            actual = amounts[name]
            min_amount = target * self.lower_bound
            max_amount = target * self.upper_bound
            deviation = actual - target
            deviation_percent = (deviation / target) * 100 if target > 0 else 0
            
            status = "✅" if actual > target else "⚠️" if actual >= target else "❌"
            print(f"\n{name} {status}:")
            print(f"  目标额度: {target:.2f}元")
            print(f"  实际分配: {actual:.2f}元")
            print(f"  允许范围: {min_amount:.2f}元 - {max_amount:.2f}元")
            print(f"  偏差: {deviation:+.2f}元 ({deviation_percent:+.2f}%)")
            
            # 检查是否满足约束
            if min_amount <= actual <= max_amount:
                print("  ✅ 分配符合要求")
            else:
                print("  ⚠️ 分配不符合要求！")
                all_valid = False
            
            print(f"  分配的发票 ({len(allocation[name])}张):")
            for filename, amount in allocation[name]:
                print(f"    - {filename} ({amount:.2f}元)")
                total_used += amount
                total_invoices_used += 1
            
            total_score += self.calculate_score(actual, target)
        
        # 显示未使用的发票
        used_invoices = set()
        for invoices in allocation.values():
            for filename, _ in invoices:
                used_invoices.add(filename)
        
        unused_invoices = [(f, a) for f, a in self.invoices if f not in used_invoices]
        
        if unused_invoices:
            print(f"\n未使用的发票 ({len(unused_invoices)}张):")
            for filename, amount in unused_invoices:
                print(f"  - {filename} ({amount:.2f}元)")
        
        print("\n" + "="*60)
        print(f"总体评估:")
        print(f"使用的发票数量: {total_invoices_used}/{len(self.invoices)}")
        print(f"使用的总金额: {total_used:.2f}元")
        print(f"超额人数: {excess_count}/{len(self.people)}")
        print(f"总得分: {total_score:.4f}")
        
        if all_valid:
            print("✅ 所有分配均满足要求！")
        else:
            print("⚠️ 部分分配未满足要求")
        
        return allocation
    
    def process_files(self, allocation):
        """处理文件：创建文件夹、复制并重命名发票文件"""
        print("\n" + "="*60)
        print("开始处理发票文件...")
        print("="*60)
        
        # 创建输出目录
        output_dir = os.path.join(self.folder_path, "发票分配结果")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建输出目录: {output_dir}")
        
        # 为每个人创建文件夹并处理文件
        for name in self.people:
            # 创建个人文件夹
            person_dir = os.path.join(output_dir, name)
            if not os.path.exists(person_dir):
                os.makedirs(person_dir)
                print(f"创建个人文件夹: {person_dir}")
            
            # 处理该人的所有发票文件
            file_count = 0
            for filename, amount in allocation[name]:
                # 构建新文件名（将原文件名中的人名替换为分配的人名）
                new_filename = self.rename_invoice_file(filename, name)
                
                # 源文件路径
                source_path = os.path.join(self.folder_path, filename)
                
                # 目标文件路径
                dest_path = os.path.join(person_dir, new_filename)
                
                # 复制文件
                try:
                    shutil.copy2(source_path, dest_path)
                    print(f"复制: {filename} -> {name}/{new_filename}")
                    file_count += 1
                except Exception as e:
                    print(f"错误: 无法复制文件 {filename} -> {new_filename}: {str(e)}")
            
            print(f"{name} 文件夹: 成功复制 {file_count} 个文件")
        
        print(f"\n所有文件处理完成！结果保存在: {output_dir}")
        return output_dir
    
    def rename_invoice_file(self, filename, new_person_name):
        """重命名发票文件，将原文件名中的人名替换为新的人名"""
        # 移除文件扩展名
        name_without_ext, ext = os.path.splitext(filename)
        
        # 提取金额部分（假设金额在文件名最后）
        # 使用正则表达式匹配金额和可能的副本标记
        amount_pattern = re.compile(r'(\d+\.?\d*)\s*(?:\(\d+\))?$')
        match = amount_pattern.search(name_without_ext)
        
        if match:
            # 提取金额部分
            amount_part = match.group(0)
            
            # 构建新文件名：新的人名 + 金额部分 + 扩展名
            new_filename = f"{new_person_name} {amount_part}{ext}"
        else:
            # 如果无法提取金额，保留原文件名但替换开头的人名部分
            # 假设原文件名格式为 "人名 其他内容"
            parts = name_without_ext.split(' ', 1)
            if len(parts) > 1:
                # 替换第一部分（人名）为新的人名
                new_filename = f"{new_person_name} {parts[1]}{ext}"
            else:
                # 如果无法分割，直接使用新人名
                new_filename = f"{new_person_name}{ext}"
        
        return new_filename
    
    def confirm_action(self, prompt):
        """确认用户操作"""
        while True:
            choice = input(prompt).strip().lower()
            if choice in ['y', 'yes', '是']:
                return True
            elif choice in ['n', 'no', '否']:
                return False
            else:
                print("请输入 y 或 n")
    
    def run(self):
        """运行主程序"""
        try:
            # 获取用户输入
            self.get_user_input()
            
            # 扫描发票文件
            if not self.scan_invoices():
                return
            
            # 主循环，允许重新计算
            while True:
                # 寻找最优分配
                allocation, amounts = self.find_optimal_allocation()
                
                if allocation is None:
                    print("无法找到满足要求的分配方案！")
                    if not self.confirm_action("\n是否重新计算？(y/n): "):
                        break
                    continue
                
                # 显示方案
                allocation = self.display_solution(allocation, amounts)
                
                # 询问用户操作
                print("\n请选择操作:")
                print("1. 处理文件（创建文件夹并复制文件）")
                print("2. 重新计算分配方案")
                print("3. 退出程序")
                
                while True:
                    choice = input("请输入选择 (1-3): ").strip()
                    if choice == '1':
                        # 处理文件
                        output_dir = self.process_files(allocation)
                        print(f"\n处理完成！")
                        print(f"分配的发票已复制到: {output_dir}")
                        print(f"每个人对应的文件夹中，文件名已更新为对应的人名")
                        
                        # 询问是否继续
                        if self.confirm_action("\n是否重新计算新的分配方案？(y/n): "):
                            break
                        else:
                            return
                    elif choice == '2':
                        # 重新计算
                        break
                    elif choice == '3':
                        # 退出程序
                        return
                    else:
                        print("无效选择，请重新输入")
                
                # 如果是重新计算，继续循环
                if choice == '2':
                    continue
            
        except KeyboardInterrupt:
            print("\n程序被用户中断")
        except Exception as e:
            print(f"程序运行出错: {str(e)}")
            import traceback
            traceback.print_exc()

# 使用示例
if __name__ == "__main__":
    allocator = InvoiceAllocator()
    allocator.run()

#!/bin/bash

# 股價預測應用 Docker 構建和運行腳本

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 應用名稱和版本
APP_NAME="stock-price-predictor"
VERSION=${1:-"latest"}

echo -e "${BLUE}🚀 股價預測應用 Docker 部署腳本${NC}"
echo -e "${BLUE}========================================${NC}"

# 函數：構建Docker映像
build_image() {
    echo -e "\n${YELLOW}📦 正在構建 Docker 映像...${NC}"
    docker build -t ${APP_NAME}:${VERSION} .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Docker 映像構建成功！${NC}"
    else
        echo -e "${RED}❌ Docker 映像構建失敗！${NC}"
        exit 1
    fi
}

# 函數：運行容器
run_container() {
    echo -e "\n${YELLOW}🏃 正在啟動容器...${NC}"
    
    # 停止舊容器（如果存在）
    docker stop ${APP_NAME} 2>/dev/null || true
    docker rm ${APP_NAME} 2>/dev/null || true
    
    # 啟動新容器
    docker run -d \
        --name ${APP_NAME} \
        -p 8000:8000 \
        --restart unless-stopped \
        ${APP_NAME}:${VERSION}
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 容器啟動成功！${NC}"
        echo -e "${GREEN}🌐 應用已在 http://localhost:8000 運行${NC}"
    else
        echo -e "${RED}❌ 容器啟動失敗！${NC}"
        exit 1
    fi
}

# 函數：顯示狀態
show_status() {
    echo -e "\n${BLUE}📊 容器狀態：${NC}"
    docker ps -f name=${APP_NAME}
    
    echo -e "\n${BLUE}📝 容器日誌：${NC}"
    docker logs --tail 10 ${APP_NAME}
}

# 主要執行流程
case "${2:-all}" in
    "build")
        build_image
        ;;
    "run")
        run_container
        ;;
    "status")
        show_status
        ;;
    "all"|*)
        build_image
        run_container
        show_status
        ;;
esac

echo -e "\n${GREEN}🎉 部署完成！${NC}"
echo -e "${BLUE}💡 常用命令：${NC}"
echo -e "  - 查看容器狀態: ${YELLOW}docker ps${NC}"
echo -e "  - 查看日誌: ${YELLOW}docker logs ${APP_NAME}${NC}"
echo -e "  - 停止容器: ${YELLOW}docker stop ${APP_NAME}${NC}"
echo -e "  - 重啟容器: ${YELLOW}docker restart ${APP_NAME}${NC}"
/////////////////////////////////////////////////////////////////////////
///@file market_data_server.cpp
///@brief	行情数据WebSocket服务器实现
///@copyright	QuantAxis版权所有
/////////////////////////////////////////////////////////////////////////

#include "market_data_server.h"
#include <iostream>
#include <sstream>
#include <cstring>
#include <chrono>
#include <iomanip>
#include <random>
#include <algorithm>

// WebSocketSession实现
WebSocketSession::WebSocketSession(tcp::socket&& socket, MarketDataServer* server)
    : ws_(std::move(socket))
    , server_(server)
    , is_writing_(false)
{
    // 生成唯一的session ID
    session_id_ = server_->create_session_id();
}

WebSocketSession::~WebSocketSession()
{
    if (server_) {
        server_->remove_session(session_id_);
    }
}

void WebSocketSession::run()
{
    // 设置WebSocket选项
    ws_.set_option(websocket::stream_base::timeout::suggested(beast::role_type::server));
    ws_.set_option(websocket::stream_base::decorator(
        [](websocket::response_type& res)
        {
            res.set(http::field::server, "QuantAxis-MarketData-Server");
        }));

    // 接受WebSocket握手
    ws_.async_accept(
        beast::bind_front_handler(&WebSocketSession::on_accept, shared_from_this()));
}

void WebSocketSession::on_accept(beast::error_code ec)
{
    if (ec) {
        server_->log_error("WebSocket accept error: " + ec.message());
        return;
    }

    server_->log_info("WebSocket session connected: " + session_id_);
    
    // 发送欢迎消息
    rapidjson::Document welcome;
    welcome.SetObject();
    rapidjson::Document::AllocatorType& allocator = welcome.GetAllocator();
    
    welcome.AddMember("type", "welcome", allocator);
    welcome.AddMember("message", "Connected to QuantAxis MarketData Server", allocator);
    welcome.AddMember("session_id", rapidjson::StringRef(session_id_.c_str()), allocator);
    welcome.AddMember("ctp_connected", server_->is_ctp_connected(), allocator);
    welcome.AddMember("timestamp", std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count(), allocator);
    
    send_response("welcome", welcome);
    
    // 开始读取消息
    do_read();
}

void WebSocketSession::do_read()
{
    ws_.async_read(
        buffer_,
        beast::bind_front_handler(&WebSocketSession::on_read, shared_from_this()));
}

void WebSocketSession::on_read(beast::error_code ec, std::size_t bytes_transferred)
{
    boost::ignore_unused(bytes_transferred);

    if (ec == websocket::error::closed) {
        server_->log_info("WebSocket session closed: " + session_id_);
        return;
    }

    if (ec) {
        server_->log_error("WebSocket read error: " + ec.message());
        return;
    }

    // 处理接收到的消息
    std::string message = beast::buffers_to_string(buffer_.data());
    buffer_.clear();
    
    handle_message(message);
    
    // 继续读取下一条消息
    do_read();
}

void WebSocketSession::handle_message(const std::string& message)
{
    server_->log_info("Received message from session " + session_id_ + ": " + message);
    
    try {
        rapidjson::Document doc;
        if (doc.Parse(message.c_str()).HasParseError()) {
            send_error("Invalid JSON format");
            return;
        }
        
        if (!doc.HasMember("action") || !doc["action"].IsString()) {
            send_error("Missing or invalid 'action' field");
            return;
        }
        
        std::string action = doc["action"].GetString();
        
        if (action == "subscribe") {
            if (!doc.HasMember("instruments") || !doc["instruments"].IsArray()) {
                send_error("Missing or invalid 'instruments' field");
                return;
            }
            
            const auto& instruments = doc["instruments"].GetArray();
            for (const auto& inst : instruments) {
                if (inst.IsString()) {
                    std::string instrument_id = inst.GetString();
                    subscriptions_.insert(instrument_id);
                    server_->subscribe_instrument(session_id_, instrument_id);
                }
            }
            
            rapidjson::Document response;
            response.SetObject();
            auto& allocator = response.GetAllocator();
            response.AddMember("type", "subscribe_response", allocator);
            response.AddMember("status", "success", allocator);
            response.AddMember("subscribed_count", static_cast<int>(subscriptions_.size()), allocator);
            
            send_response("subscribe_response", response);
            
        } else if (action == "unsubscribe") {
            if (!doc.HasMember("instruments") || !doc["instruments"].IsArray()) {
                send_error("Missing or invalid 'instruments' field");
                return;
            }
            
            const auto& instruments = doc["instruments"].GetArray();
            for (const auto& inst : instruments) {
                if (inst.IsString()) {
                    std::string instrument_id = inst.GetString();
                    subscriptions_.erase(instrument_id);
                    server_->unsubscribe_instrument(session_id_, instrument_id);
                }
            }
            
            rapidjson::Document response;
            response.SetObject();
            auto& allocator = response.GetAllocator();
            response.AddMember("type", "unsubscribe_response", allocator);
            response.AddMember("status", "success", allocator);
            response.AddMember("subscribed_count", static_cast<int>(subscriptions_.size()), allocator);
            
            send_response("unsubscribe_response", response);
            
        } else if (action == "list_instruments") {
            auto instruments = server_->get_all_instruments();
            
            rapidjson::Document response;
            response.SetObject();
            auto& allocator = response.GetAllocator();
            response.AddMember("type", "instrument_list", allocator);
            
            rapidjson::Value inst_array(rapidjson::kArrayType);
            for (const auto& inst : instruments) {
                inst_array.PushBack(rapidjson::StringRef(inst.c_str()), allocator);
            }
            response.AddMember("instruments", inst_array, allocator);
            response.AddMember("count", static_cast<int>(instruments.size()), allocator);
            
            send_response("instrument_list", response);
            
        } else if (action == "search_instruments") {
            if (!doc.HasMember("pattern") || !doc["pattern"].IsString()) {
                send_error("Missing or invalid 'pattern' field");
                return;
            }
            
            std::string pattern = doc["pattern"].GetString();
            auto instruments = server_->search_instruments(pattern);
            
            rapidjson::Document response;
            response.SetObject();
            auto& allocator = response.GetAllocator();
            response.AddMember("type", "search_result", allocator);
            response.AddMember("pattern", rapidjson::StringRef(pattern.c_str()), allocator);
            
            rapidjson::Value inst_array(rapidjson::kArrayType);
            for (const auto& inst : instruments) {
                inst_array.PushBack(rapidjson::StringRef(inst.c_str()), allocator);
            }
            response.AddMember("instruments", inst_array, allocator);
            response.AddMember("count", static_cast<int>(instruments.size()), allocator);
            
            send_response("search_result", response);
            
        } else {
            send_error("Unknown action: " + action);
        }
        
    } catch (const std::exception& e) {
        send_error("Error processing message: " + std::string(e.what()));
    }
}

void WebSocketSession::send_error(const std::string& error_msg)
{
    rapidjson::Document error;
    error.SetObject();
    auto& allocator = error.GetAllocator();
    error.AddMember("type", "error", allocator);
    error.AddMember("message", rapidjson::StringRef(error_msg.c_str()), allocator);
    error.AddMember("timestamp", std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count(), allocator);
    
    send_response("error", error);
}

void WebSocketSession::send_response(const std::string& type, const rapidjson::Document& data)
{
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    data.Accept(writer);
    
    send_message(buffer.GetString());
}

void WebSocketSession::send_message(const std::string& message)
{
    std::lock_guard<std::mutex> lock(write_mutex_);
    
    message_queue_.push(message);
    
    if (!is_writing_) {
        is_writing_ = true;
        start_write();
    }
}

void WebSocketSession::start_write()
{
    if (message_queue_.empty()) {
        is_writing_ = false;
        return;
    }

    std::string message = message_queue_.front();
    message_queue_.pop();

    ws_.async_write(
        net::buffer(message),
        beast::bind_front_handler(&WebSocketSession::on_write, shared_from_this()));
}

void WebSocketSession::on_write(beast::error_code ec, std::size_t bytes_transferred)
{
    boost::ignore_unused(bytes_transferred);

    if (ec) {
        server_->log_error("WebSocket write error: " + ec.message());
        std::lock_guard<std::mutex> lock(write_mutex_);
        is_writing_ = false;
        return;
    }

    std::lock_guard<std::mutex> lock(write_mutex_);
    
    // 继续写入队列中的下一条消息
    start_write();
}

void WebSocketSession::close()
{
    beast::error_code ec;
    ws_.close(websocket::close_code::normal, ec);
    if (ec) {
        server_->log_error("Error closing WebSocket: " + ec.message());
    }
}

// MarketDataSpi实现
MarketDataSpi::MarketDataSpi(MarketDataServer* server) : server_(server)
{
}

MarketDataSpi::~MarketDataSpi()
{
}

void MarketDataSpi::OnFrontConnected()
{
    server_->log_info("CTP front connected");
    server_->ctp_login();
}

void MarketDataSpi::OnFrontDisconnected(int nReason)
{
    server_->log_warning("CTP front disconnected, reason: " + std::to_string(nReason));
}

void MarketDataSpi::OnRspUserLogin(CThostFtdcRspUserLoginField *pRspUserLogin,
                                  CThostFtdcRspInfoField *pRspInfo,
                                  int nRequestID, bool bIsLast)
{
    if (pRspInfo && pRspInfo->ErrorID != 0) {
        server_->log_error("CTP login failed: " + std::string(pRspInfo->ErrorMsg));
        return;
    }
    
    server_->log_info("CTP login successful");
}

void MarketDataSpi::OnRspSubMarketData(CThostFtdcSpecificInstrumentField *pSpecificInstrument,
                                      CThostFtdcRspInfoField *pRspInfo,
                                      int nRequestID, bool bIsLast)
{
    if (pRspInfo && pRspInfo->ErrorID != 0) {
        server_->log_error("Subscribe market data failed: " + std::string(pRspInfo->ErrorMsg));
        return;
    }
    
    if (pSpecificInstrument) {
        server_->log_info("Subscribed to instrument: " + std::string(pSpecificInstrument->InstrumentID));
    }
}

void MarketDataSpi::OnRtnDepthMarketData(CThostFtdcDepthMarketDataField *pDepthMarketData)
{
    if (!pDepthMarketData) return;
    
    // Debug打印行情数据接收信息
    server_->log_info("DEBUG: Received market data for instrument: " + std::string(pDepthMarketData->InstrumentID) + 
                     ", price: " + std::to_string(pDepthMarketData->LastPrice) + 
                     ", volume: " + std::to_string(pDepthMarketData->Volume));
    
    // 构建JSON格式的行情数据
    rapidjson::Document market_data;
    market_data.SetObject();
    auto& allocator = market_data.GetAllocator();
    
    market_data.AddMember("type", "market_data", allocator);
    market_data.AddMember("instrument_id", rapidjson::StringRef(pDepthMarketData->InstrumentID), allocator);
    market_data.AddMember("trading_day", rapidjson::StringRef(pDepthMarketData->TradingDay), allocator);
    market_data.AddMember("update_time", rapidjson::StringRef(pDepthMarketData->UpdateTime), allocator);
    market_data.AddMember("last_price", pDepthMarketData->LastPrice, allocator);
    market_data.AddMember("pre_settlement_price", pDepthMarketData->PreSettlementPrice, allocator);
    market_data.AddMember("pre_close_price", pDepthMarketData->PreClosePrice, allocator);
    market_data.AddMember("open_price", pDepthMarketData->OpenPrice, allocator);
    market_data.AddMember("highest_price", pDepthMarketData->HighestPrice, allocator);
    market_data.AddMember("lowest_price", pDepthMarketData->LowestPrice, allocator);
    market_data.AddMember("volume", pDepthMarketData->Volume, allocator);
    market_data.AddMember("turnover", pDepthMarketData->Turnover, allocator);
    market_data.AddMember("open_interest", pDepthMarketData->OpenInterest, allocator);
    market_data.AddMember("upper_limit_price", pDepthMarketData->UpperLimitPrice, allocator);
    market_data.AddMember("lower_limit_price", pDepthMarketData->LowerLimitPrice, allocator);
    
    // 买卖五档
    market_data.AddMember("bid_price1", pDepthMarketData->BidPrice1, allocator);
    market_data.AddMember("bid_volume1", pDepthMarketData->BidVolume1, allocator);
    market_data.AddMember("ask_price1", pDepthMarketData->AskPrice1, allocator);
    market_data.AddMember("ask_volume1", pDepthMarketData->AskVolume1, allocator);
    
    market_data.AddMember("timestamp", std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count(), allocator);
    
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    market_data.Accept(writer);
    
    // 存储到Redis
    std::string json_data = buffer.GetString();
    std::string instrument_id = pDepthMarketData->InstrumentID;
    
    auto& redis_client = server_->get_redis_client();
    if (redis_client && redis_client->is_connected()) {
        // 存储最新行情数据到Redis，使用Hash结构
        std::string redis_key = "market_data:" + instrument_id;
        if (!redis_client->set(redis_key, json_data)) {
            server_->log_warning("Failed to store market data to Redis for instrument: " + instrument_id);
        }
        
        // 也可以存储到Hash中以便按字段查询
        std::string hash_key = "market_data_hash:" + instrument_id;
        redis_client->hset(hash_key, "last_price", std::to_string(pDepthMarketData->LastPrice));
        redis_client->hset(hash_key, "volume", std::to_string(pDepthMarketData->Volume));
        redis_client->hset(hash_key, "update_time", pDepthMarketData->UpdateTime);
        redis_client->hset(hash_key, "trading_day", pDepthMarketData->TradingDay);
        redis_client->hset(hash_key, "json_data", json_data);
    }
    
    // 广播行情数据
    server_->broadcast_market_data(instrument_id, json_data);
}

void MarketDataSpi::OnRspError(CThostFtdcRspInfoField *pRspInfo, int nRequestID, bool bIsLast)
{
    if (pRspInfo && pRspInfo->ErrorID != 0) {
        server_->log_error("CTP error: " + std::string(pRspInfo->ErrorMsg));
    }
}

// MarketDataServer实现
MarketDataServer::MarketDataServer(const std::string& ctp_front_addr,
                                 const std::string& broker_id,
                                 int websocket_port)
    : ctp_front_addr_(ctp_front_addr)
    , broker_id_(broker_id)
    , ioc_()
    , websocket_port_(websocket_port)
    , ctp_api_(nullptr)
    , ctp_connected_(false)
    , ctp_logged_in_(false)
    , acceptor_(ioc_)
    , segment_(nullptr)
    , alloc_inst_(nullptr)
    , ins_map_(nullptr)
    , is_running_(false)
    , request_id_(0)
    , use_multi_ctp_mode_(false)
    , redis_client_(std::make_unique<RedisClient>("192.168.2.27", 6379))
{
}

MarketDataServer::MarketDataServer(const MultiCTPConfig& config)
    : broker_id_(config.connections.empty() ? "9999" : config.connections[0].broker_id)
    , ioc_()
    , websocket_port_(config.websocket_port)
    , ctp_api_(nullptr)
    , ctp_connected_(false)
    , ctp_logged_in_(false)
    , acceptor_(ioc_)
    , segment_(nullptr)
    , alloc_inst_(nullptr)
    , ins_map_(nullptr)
    , multi_ctp_config_(config)
    , use_multi_ctp_mode_(true)
    , is_running_(false)
    , request_id_(0)
    , redis_client_(std::make_unique<RedisClient>(config.redis_host, config.redis_port))
{
}

MarketDataServer::~MarketDataServer()
{
    stop();
    cleanup_shared_memory();
    if (use_multi_ctp_mode_) {
        cleanup_multi_ctp_system();
    }
}

bool MarketDataServer::start()
{
    if (is_running_) {
        return true;
    }
    
    std::string mode = use_multi_ctp_mode_ ? "multi-CTP" : "single-CTP";
    log_info("Starting MarketData Server in " + mode + " mode...");
    
    try {
        // 初始化共享内存
        init_shared_memory();
        
        // 初始化Redis连接
        std::string redis_info;
        if (use_multi_ctp_mode_) {
            redis_info = multi_ctp_config_.redis_host + ":" + std::to_string(multi_ctp_config_.redis_port);
        } else {
            redis_info = "192.168.2.27:6379";
        }
            
        if (!redis_client_->connect()) {
            log_error("Failed to connect to Redis server at " + redis_info);
            log_warning("Market data will not be stored in Redis");
        } else {
            log_info("Connected to Redis server at " + redis_info);
        }
        
        // 启动WebSocket服务器
        start_websocket_server();
        
        if (use_multi_ctp_mode_) {
            // 多CTP连接模式
            if (!init_multi_ctp_system()) {
                log_error("Failed to initialize multi-CTP system");
                return false;
            }
        } else {
            // 单CTP连接模式（兼容性）
            std::string flow_path = "./ctpflow/single/";
            
            // 确保flow目录存在
            std::string mkdir_cmd = "mkdir -p " + flow_path;
            if (system(mkdir_cmd.c_str()) != 0) {
                log_warning("Failed to create flow directory: " + flow_path);
            }
            
            ctp_api_ = CThostFtdcMdApi::CreateFtdcMdApi(flow_path.c_str());
            if (!ctp_api_) {
                log_error("Failed to create CTP API");
                return false;
            }
            
            md_spi_ = std::make_unique<MarketDataSpi>(this);
            ctp_api_->RegisterSpi(md_spi_.get());
            ctp_api_->RegisterFront(const_cast<char*>(ctp_front_addr_.c_str()));
            ctp_api_->Init();
        }
        
        is_running_ = true;
        
        // 启动服务器线程
        server_thread_ = boost::thread([this]() {
            ioc_.run();
        });
        
        log_info("MarketData Server started on port " + std::to_string(websocket_port_));
        return true;
        
    } catch (const std::exception& e) {
        log_error("Failed to start server: " + std::string(e.what()));
        return false;
    }
}

void MarketDataServer::stop()
{
    if (!is_running_) {
        return;
    }
    
    log_info("Stopping MarketData Server...");
    is_running_ = false;
    
    // 关闭所有WebSocket连接
    {
        std::lock_guard<std::mutex> lock(sessions_mutex_);
        for (auto& pair : sessions_) {
            pair.second->close();
        }
        sessions_.clear();
    }
    
    // 停止IO上下文
    ioc_.stop();
    
    // 等待服务器线程结束
    if (server_thread_.joinable()) {
        server_thread_.join();
    }
    
    // 清理CTP资源
    if (ctp_api_) {
        ctp_api_->Release();
        ctp_api_ = nullptr;
    }
    
    log_info("MarketData Server stopped");
}

void MarketDataServer::init_shared_memory()
{
    try {
        // 尝试连接到现有的共享内存段
        segment_ = new boost::interprocess::managed_shared_memory(
            boost::interprocess::open_only, "qamddata");
        
        alloc_inst_ = new ShmemAllocator(segment_->get_segment_manager());
        ins_map_ = segment_->find<InsMapType>("InsMap").first;
        
        if (ins_map_) {
            log_info("Connected to existing shared memory segment with " + 
                    std::to_string(ins_map_->size()) + " instruments");
        } else {
            log_warning("Shared memory segment found but InsMap not found");
        }
        
    } catch (const boost::interprocess::interprocess_exception& e) {
        log_warning("Failed to connect to existing shared memory: " + std::string(e.what()));
        log_info("Creating new shared memory segment");
        
        try {
            boost::interprocess::shared_memory_object::remove("qamddata");
            
            segment_ = new boost::interprocess::managed_shared_memory(
                boost::interprocess::create_only,
                "qamddata",
                32 * 1024 * 1024);  // 32MB
            
            alloc_inst_ = new ShmemAllocator(segment_->get_segment_manager());
            ins_map_ = segment_->construct<InsMapType>("InsMap")(
                CharArrayComparer(), *alloc_inst_);
            
            log_info("Created new shared memory segment");
            
        } catch (const std::exception& e) {
            log_error("Failed to create shared memory: " + std::string(e.what()));
            throw;
        }
    }
}

void MarketDataServer::cleanup_shared_memory()
{
    if (alloc_inst_) {
        delete alloc_inst_;
        alloc_inst_ = nullptr;
    }
    
    if (segment_) {
        delete segment_;
        segment_ = nullptr;
    }
    
    ins_map_ = nullptr;
}

void MarketDataServer::start_websocket_server()
{
    auto const address = net::ip::make_address("0.0.0.0");
    auto const port = static_cast<unsigned short>(websocket_port_);
    
    tcp::endpoint endpoint{address, port};
    acceptor_.open(endpoint.protocol());
    acceptor_.set_option(net::socket_base::reuse_address(true));
    acceptor_.bind(endpoint);
    acceptor_.listen(net::socket_base::max_listen_connections);
    
    // 开始接受连接
    acceptor_.async_accept(
        net::make_strand(ioc_),
        beast::bind_front_handler(&MarketDataServer::handle_accept, this));
}

void MarketDataServer::handle_accept(beast::error_code ec, tcp::socket socket)
{
    if (ec) {
        log_error("Accept error: " + ec.message());
    } else {
        // 创建新的会话
        auto session = std::make_shared<WebSocketSession>(std::move(socket), this);
        add_session(session);
        session->run();
    }
    
    // 继续接受连接
    acceptor_.async_accept(
        net::make_strand(ioc_),
        beast::bind_front_handler(&MarketDataServer::handle_accept, this));
}

void MarketDataServer::ctp_login()
{
    CThostFtdcReqUserLoginField req;
    memset(&req, 0, sizeof(req));
    
    // 行情API登录只需要BrokerID，不需要用户名和密码
    strcpy(req.BrokerID, broker_id_.c_str());
    // 行情登录可以使用空的用户ID和密码
    strcpy(req.UserID, "");
    strcpy(req.Password, "");
    
    int ret = ctp_api_->ReqUserLogin(&req, ++request_id_);
    if (ret != 0) {
        log_error("Failed to send market data login request, return code: " + std::to_string(ret));
    } else {
        ctp_connected_ = true;
        ctp_logged_in_ = true;
        log_info("Market data login request sent");
    }
}

std::string MarketDataServer::create_session_id()
{
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(100000, 999999);
    
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;
    
    std::ostringstream oss;
    oss << "session_" << time_t << "_" << ms.count() << "_" << dis(gen);
    return oss.str();
}

void MarketDataServer::add_session(std::shared_ptr<WebSocketSession> session)
{
    std::lock_guard<std::mutex> lock(sessions_mutex_);
    sessions_[session->get_session_id()] = session;
}

void MarketDataServer::remove_session(const std::string& session_id)
{
    if (use_multi_ctp_mode_) {
        // 多CTP连接模式：使用订阅分发器
        if (subscription_dispatcher_) {
            subscription_dispatcher_->remove_all_subscriptions_for_session(session_id);
        }
    } else {
        // 单CTP连接模式（兼容性）
        std::lock_guard<std::mutex> lock2(subscribers_mutex_);
        
        auto it = sessions_.find(session_id);
        if (it != sessions_.end()) {
            // 移除该会话的所有订阅
            const auto& subscriptions = it->second->get_subscriptions();
            for (const auto& instrument_id : subscriptions) {
                auto sub_it = instrument_subscribers_.find(instrument_id);
                if (sub_it != instrument_subscribers_.end()) {
                    sub_it->second.erase(session_id);
                    // 如果没有会话订阅该合约了，从CTP取消订阅
                    if (sub_it->second.empty()) {
                        instrument_subscribers_.erase(sub_it);
                        
                        if (ctp_api_ && ctp_logged_in_) {
                            char* instruments[] = {const_cast<char*>(instrument_id.c_str())};
                            int ret = ctp_api_->UnSubscribeMarketData(instruments, 1);
                            if (ret == 0) {
                                log_info("Auto-unsubscribed from CTP market data: " + instrument_id + 
                                       " (session disconnected)");
                            } else {
                                log_error("Failed to auto-unsubscribe from CTP market data: " + instrument_id +
                                         ", return code: " + std::to_string(ret));
                            }
                        }
                    }
                }
            }
        }
    }
    
    // 通用的session移除逻辑
    std::lock_guard<std::mutex> lock1(sessions_mutex_);
    auto it = sessions_.find(session_id);
    if (it != sessions_.end()) {
        sessions_.erase(it);
        log_info("Session removed: " + session_id);
    }
}

void MarketDataServer::subscribe_instrument(const std::string& session_id, const std::string& instrument_id)
{
    if (use_multi_ctp_mode_) {
        // 多CTP连接模式：使用订阅分发器
        if (subscription_dispatcher_) {
            subscription_dispatcher_->add_subscription(session_id, instrument_id);
        }
    } else {
        // 单CTP连接模式（兼容性）
        std::lock_guard<std::mutex> lock(subscribers_mutex_);
        
        instrument_subscribers_[instrument_id].insert(session_id);
        
        // 如果这是第一个订阅该合约的会话，向CTP订阅行情
        if (instrument_subscribers_[instrument_id].size() == 1 && ctp_api_ && ctp_logged_in_) {
            char* instruments[] = {const_cast<char*>(instrument_id.c_str())};
            int ret = ctp_api_->SubscribeMarketData(instruments, 1);
            if (ret == 0) {
                log_info("Subscribed to CTP market data: " + instrument_id);
            } else {
                log_error("Failed to subscribe to CTP market data: " + instrument_id + 
                         ", return code: " + std::to_string(ret));
            }
        }
    }
}

void MarketDataServer::unsubscribe_instrument(const std::string& session_id, const std::string& instrument_id)
{
    if (use_multi_ctp_mode_) {
        // 多CTP连接模式：使用订阅分发器
        if (subscription_dispatcher_) {
            subscription_dispatcher_->remove_subscription(session_id, instrument_id);
        }
    } else {
        // 单CTP连接模式（兼容性）
        std::lock_guard<std::mutex> lock(subscribers_mutex_);
        
        auto it = instrument_subscribers_.find(instrument_id);
        if (it != instrument_subscribers_.end()) {
            it->second.erase(session_id);
            
            // 如果没有会话订阅该合约了，从CTP取消订阅
            if (it->second.empty()) {
                instrument_subscribers_.erase(it);
                
                if (ctp_api_ && ctp_logged_in_) {
                    char* instruments[] = {const_cast<char*>(instrument_id.c_str())};
                    int ret = ctp_api_->UnSubscribeMarketData(instruments, 1);
                    if (ret == 0) {
                        log_info("Unsubscribed from CTP market data: " + instrument_id);
                    } else {
                        log_error("Failed to unsubscribe from CTP market data: " + instrument_id +
                                 ", return code: " + std::to_string(ret));
                    }
                }
            }
        }
    }
}

void MarketDataServer::broadcast_market_data(const std::string& instrument_id, const std::string& json_data)
{
    std::lock_guard<std::mutex> lock1(sessions_mutex_);
    std::lock_guard<std::mutex> lock2(subscribers_mutex_);
    
    auto it = instrument_subscribers_.find(instrument_id);
    if (it != instrument_subscribers_.end()) {
        for (const auto& session_id : it->second) {
            auto session_it = sessions_.find(session_id);
            if (session_it != sessions_.end()) {
                session_it->second->send_message(json_data);
            }
        }
    }
}

void MarketDataServer::send_to_session(const std::string& session_id, const std::string& message)
{
    std::lock_guard<std::mutex> lock(sessions_mutex_);
    
    auto it = sessions_.find(session_id);
    if (it != sessions_.end()) {
        it->second->send_message(message);
    }
}

std::vector<std::string> MarketDataServer::get_all_instruments()
{
    std::vector<std::string> instruments;
    
    if (ins_map_) {
        for (auto it = ins_map_->begin(); it != ins_map_->end(); ++it) {
            std::string key(it->first.data());
            // 移除末尾的空字符
            key.erase(std::find(key.begin(), key.end(), '\0'), key.end());
            if (!key.empty()) {
                instruments.push_back(key);
            }
        }
    }
    
    return instruments;
}

std::vector<std::string> MarketDataServer::search_instruments(const std::string& pattern)
{
    std::vector<std::string> matching_instruments;
    
    if (ins_map_) {
        std::string lower_pattern = pattern;
        std::transform(lower_pattern.begin(), lower_pattern.end(), lower_pattern.begin(), ::tolower);
        
        for (auto it = ins_map_->begin(); it != ins_map_->end(); ++it) {
            std::string key(it->first.data());
            key.erase(std::find(key.begin(), key.end(), '\0'), key.end());
            
            if (!key.empty()) {
                std::string lower_key = key;
                std::transform(lower_key.begin(), lower_key.end(), lower_key.begin(), ::tolower);
                
                if (lower_key.find(lower_pattern) != std::string::npos) {
                    matching_instruments.push_back(key);
                }
            }
        }
    }
    
    return matching_instruments;
}

void MarketDataServer::log_info(const std::string& message)
{
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    
    std::cout << "[" << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S") 
              << "] [INFO] " << message << std::endl;
}

void MarketDataServer::log_error(const std::string& message)
{
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    
    std::cerr << "[" << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S") 
              << "] [ERROR] " << message << std::endl;
}

void MarketDataServer::log_warning(const std::string& message)
{
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    
    std::cout << "[" << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S") 
              << "] [WARNING] " << message << std::endl;
}

// 多CTP系统实现
bool MarketDataServer::init_multi_ctp_system()
{
    log_info("Initializing multi-CTP system...");
    
    try {
        // 创建订阅分发器
        subscription_dispatcher_ = std::make_unique<SubscriptionDispatcher>(this);
        
        // 创建连接管理器
        connection_manager_ = std::make_unique<CTPConnectionManager>(this, subscription_dispatcher_.get());
        
        // 初始化订阅分发器
        if (!subscription_dispatcher_->initialize(connection_manager_.get())) {
            log_error("Failed to initialize subscription dispatcher");
            return false;
        }
        
        // 设置负载均衡策略
        subscription_dispatcher_->set_load_balance_strategy(multi_ctp_config_.load_balance_strategy);
        
        // 添加所有连接配置
        for (const auto& conn_config : multi_ctp_config_.connections) {
            if (conn_config.enabled) {
                if (!connection_manager_->add_connection(conn_config)) {
                    log_error("Failed to add connection: " + conn_config.connection_id);
                    return false;
                }
                log_info("Added CTP connection: " + conn_config.connection_id + 
                        " -> " + conn_config.front_addr);
            } else {
                log_info("Skipped disabled connection: " + conn_config.connection_id);
            }
        }
        
        // 启动所有连接
        if (!connection_manager_->start_all_connections()) {
            log_warning("Some CTP connections failed to start");
        }
        
        log_info("Multi-CTP system initialized successfully with " + 
                std::to_string(connection_manager_->get_total_connections()) + " connections");
        return true;
        
    } catch (const std::exception& e) {
        log_error("Exception initializing multi-CTP system: " + std::string(e.what()));
        return false;
    }
}

void MarketDataServer::cleanup_multi_ctp_system()
{
    if (connection_manager_) {
        connection_manager_->stop_all_connections();
        connection_manager_.reset();
    }
    
    if (subscription_dispatcher_) {
        subscription_dispatcher_->shutdown();
        subscription_dispatcher_.reset();
    }
    
    log_info("Multi-CTP system cleaned up");
}

// 多连接版本的状态查询
bool MarketDataServer::is_ctp_connected() const
{
    if (use_multi_ctp_mode_) {
        return connection_manager_ && connection_manager_->get_active_connections() > 0;
    } else {
        return ctp_connected_;
    }
}

bool MarketDataServer::is_ctp_logged_in() const
{
    if (use_multi_ctp_mode_) {
        return connection_manager_ && connection_manager_->get_active_connections() > 0;
    } else {
        return ctp_logged_in_;
    }
}

size_t MarketDataServer::get_active_connections_count() const
{
    if (use_multi_ctp_mode_ && connection_manager_) {
        return connection_manager_->get_active_connections();
    }
    return ctp_logged_in_ ? 1 : 0;
}

std::vector<std::string> MarketDataServer::get_connection_status() const
{
    std::vector<std::string> status_list;
    
    if (use_multi_ctp_mode_ && connection_manager_) {
        auto connections = connection_manager_->get_all_connections();
        for (const auto& conn : connections) {
            std::string status = conn->get_connection_id() + ": ";
            switch (conn->get_status()) {
                case CTPConnectionStatus::DISCONNECTED:
                    status += "DISCONNECTED";
                    break;
                case CTPConnectionStatus::CONNECTING:
                    status += "CONNECTING";
                    break;
                case CTPConnectionStatus::CONNECTED:
                    status += "CONNECTED";
                    break;
                case CTPConnectionStatus::LOGGED_IN:
                    status += "LOGGED_IN (" + std::to_string(conn->get_subscription_count()) + " subs)";
                    break;
                case CTPConnectionStatus::ERROR:
                    status += "ERROR";
                    break;
            }
            status += " [Quality: " + std::to_string(conn->get_connection_quality()) + "%]";
            status_list.push_back(status);
        }
    } else {
        std::string status = "single_ctp: ";
        if (ctp_logged_in_) {
            status += "LOGGED_IN";
        } else if (ctp_connected_) {
            status += "CONNECTED";
        } else {
            status += "DISCONNECTED";
        }
        status_list.push_back(status);
    }
    
    return status_list;
}
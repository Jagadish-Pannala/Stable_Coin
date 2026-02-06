CREATE DATABASE stablecoin_bank_core;
USE stablecoin_bank_core;

-- Tenant/Organization table
CREATE TABLE tenant_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_name VARCHAR(100) NOT NULL,
    rpc_url VARCHAR(200) NOT NULL,
    chain_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_active (is_active),
    UNIQUE KEY unique_tenant_name (tenant_name)
);

-- Bank customer/user table
CREATE TABLE bank_customer_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    mail VARCHAR(150) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15),
    bank_account_number VARCHAR(30),
    password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    wallet_address VARCHAR(255),
    encrypted_private_key TEXT,
    fiat_bank_balance DECIMAL(18, 2) DEFAULT 0.00, -- Fiat balance
    is_wallet BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenant_details(id)
        ON DELETE CASCADE,
    INDEX idx_customer_tenant (tenant_id),
    INDEX idx_customer_active (is_active),
    INDEX idx_customer_mail (mail),
    INDEX idx_customer_phone (phone_number),
    INDEX idx_customer_wallet (wallet_address),
    INDEX idx_customer_bank_account (bank_account_number),
    -- Unique constraints per tenant
    UNIQUE KEY unique_tenant_customer_id (tenant_id, customer_id),
    UNIQUE KEY unique_tenant_mail (tenant_id, mail),
    UNIQUE KEY unique_tenant_phone (tenant_id, phone_number),
    UNIQUE KEY unique_tenant_bank_account (tenant_id, bank_account_number),
    UNIQUE KEY unique_tenant_wallet (tenant_id, wallet_address)
);

-- Customer's Payees (beneficiaries/recipients)
-- Using SINGLE TABLE with customer_id (NO separate mapping)
CREATE TABLE customer_payees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    payee_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    bank_account_number VARCHAR(30),
    wallet_address VARCHAR(255) NOT NULL,
    nickname VARCHAR(100), -- Customer's personal label for this payee
    notes TEXT, -- Personal notes
    is_favorite BOOLEAN DEFAULT FALSE,
    relationship_type VARCHAR(50), -- 'family', 'friend', 'business', 'merchant'
    payee_type ENUM('internal', 'external') DEFAULT 'external', -- internal = another customer in same bank
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_payee_customer
        FOREIGN KEY (customer_id)
        REFERENCES bank_customer_details(id)
        ON DELETE CASCADE,
    INDEX idx_payee_customer (customer_id),
    INDEX idx_payee_wallet (wallet_address),
    INDEX idx_payee_active (is_active),
    INDEX idx_payee_favorite (customer_id, is_favorite),
    -- Each customer can save each wallet address only once
    UNIQUE KEY unique_customer_wallet (customer_id, wallet_address)
);
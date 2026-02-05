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
    INDEX idx_tenant_active (is_active)
);

-- Bank customer/user table
CREATE TABLE bank_customer_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    mail VARCHAR(150) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15),
    bank_account_number VARCHAR(30),
    password VARCHAR(255) NOT NULL, -- Increased size for hashed passwords
    is_active BOOLEAN DEFAULT TRUE,
    wallet_address VARCHAR(255) UNIQUE,
    private_key TEXT,
    is_wallet BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenant_details(id)
        ON DELETE CASCADE,
    INDEX idx_customer_tenant (tenant_id),
    INDEX idx_customer_active (is_active),
    INDEX idx_customer_wallet (wallet_address),
    UNIQUE KEY unique_tenant_customer (tenant_id, customer_id)
);

-- Payer details table (people who send money to customers)
CREATE TABLE payer_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    wallet_address VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_payer_wallet (wallet_address)
);

-- Mapping table between customers and their payers
CREATE TABLE customer_payer_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    payer_id INT NOT NULL,
    relationship_type VARCHAR(50), -- Optional: 'trusted', 'regular', 'business', etc.
    notes TEXT, -- Optional: additional context about the relationship
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_mapping_customer
        FOREIGN KEY (user_id)
        REFERENCES bank_customer_details(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_mapping_payer
        FOREIGN KEY (payer_id)
        REFERENCES payer_details(id)
        ON DELETE CASCADE,
    UNIQUE KEY unique_customer_payer (user_id, payer_id),
    INDEX idx_mapping_user (user_id),
    INDEX idx_mapping_payer (payer_id)
);
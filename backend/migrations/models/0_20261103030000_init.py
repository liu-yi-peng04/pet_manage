"""初始结构迁移（tortoise-orm 0.22 / MySQL）。

由当前模型生成 CREATE TABLE IF NOT EXISTS，不会 DROP，也不会改写已有业务行。
已有旧库若缺列，upgrade 会再补 ADD COLUMN，并只把训犬师空文案填成空字符串或 []。

不要执行 downgrade：回滚意味着删除全部业务表。本文件直接拒绝。

已有演示库建议：
1. 备份
2. 在 backend 目录、APP_ENV=demo 且 DATABASE_URL 指向该库时执行 aerich upgrade
3. 确认数据还在后，可将 DEMO_AUTO_SCHEMA=false，避免启动时再跑 DDL

全新库直接 aerich upgrade 即可。
"""
from tortoise import BaseDBAsyncClient

from app.core.legacy_schema import assemble_upgrade_sql, pending_legacy_statements

# safe=True，重复执行不会覆盖已有表。
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS `store` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `store_type` VARCHAR(20) NOT NULL  DEFAULT 'shop',
    `address` VARCHAR(255),
    `phone` VARCHAR(32),
    `city` VARCHAR(64),
    `rating` DOUBLE NOT NULL  DEFAULT 5,
    `description` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4 COMMENT='合作商家：宠物店 / 医院 / 寄养中心 / 用品供应商。';
CREATE TABLE IF NOT EXISTS `petlisting` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(64) NOT NULL,
    `species` VARCHAR(20) NOT NULL  DEFAULT 'dog',
    `breed` VARCHAR(64),
    `gender` VARCHAR(10) NOT NULL  DEFAULT 'unknown',
    `age_months` INT,
    `price` DECIMAL(10,2),
    `health_note` VARCHAR(255),
    `vaccine_note` VARCHAR(255),
    `description` LONGTEXT NOT NULL,
    `appearance` VARCHAR(20) NOT NULL  DEFAULT 'standard',
    `color` VARCHAR(64),
    `weight_kg` DOUBLE,
    `image_url` VARCHAR(500),
    `is_active` BOOL NOT NULL  DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `store_id` INT NOT NULL,
    CONSTRAINT `fk_petlisti_store_45ae58e0` FOREIGN KEY (`store_id`) REFERENCES `store` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='门店待售/待领养宠物展示，供选宠匹配（非主人档案）。';
CREATE TABLE IF NOT EXISTS `product` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `category` VARCHAR(20) NOT NULL  DEFAULT 'supply',
    `price` DECIMAL(10,2),
    `species` VARCHAR(10) NOT NULL  DEFAULT 'both',
    `min_weight_kg` DOUBLE,
    `max_weight_kg` DOUBLE,
    `spec` VARCHAR(128),
    `image_url` VARCHAR(500),
    `description` LONGTEXT NOT NULL,
    `is_active` BOOL NOT NULL  DEFAULT 1,
    `stock` INT NOT NULL  DEFAULT 99,
    `promo` VARCHAR(128),
    `shipping_mode` VARCHAR(20) NOT NULL  DEFAULT 'instant',
    `brand` VARCHAR(64),
    `package_spec` VARCHAR(64),
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `store_id` INT,
    CONSTRAINT `fk_product_store_ec648b83` FOREIGN KEY (`store_id`) REFERENCES `store` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='在售商品：支持库存、优惠与配送方式，走平台订单履约。';
CREATE TABLE IF NOT EXISTS `user` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(64) NOT NULL UNIQUE,
    `email` VARCHAR(128)  UNIQUE,
    `hashed_password` VARCHAR(255) NOT NULL,
    `role` VARCHAR(20) NOT NULL  DEFAULT 'user',
    `staff_role` VARCHAR(20),
    `points` INT NOT NULL  DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `store_id` INT,
    CONSTRAINT `fk_user_store_cd17fe12` FOREIGN KEY (`store_id`) REFERENCES `store` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `knowledgebase` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `description` LONGTEXT NOT NULL,
    `is_public` BOOL NOT NULL  DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `owner_id` INT NOT NULL,
    `store_id` INT,
    CONSTRAINT `fk_knowledg_user_4dfbd747` FOREIGN KEY (`owner_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_knowledg_store_f550f2bd` FOREIGN KEY (`store_id`) REFERENCES `store` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `conversation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL  DEFAULT '新对话',
    `channel` VARCHAR(32) NOT NULL  DEFAULT 'user',
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `kb_id` INT,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_conversa_knowledg_d0ea26cb` FOREIGN KEY (`kb_id`) REFERENCES `knowledgebase` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_conversa_user_84883661` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `chatmessage` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `role` VARCHAR(20) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `conversation_id` INT NOT NULL,
    CONSTRAINT `fk_chatmess_conversa_b0feb1bd` FOREIGN KEY (`conversation_id`) REFERENCES `conversation` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `document` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `filename` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_type` VARCHAR(20) NOT NULL  DEFAULT 'txt',
    `status` VARCHAR(20) NOT NULL  DEFAULT 'pending',
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `kb_id` INT NOT NULL,
    CONSTRAINT `fk_document_knowledg_a8407b96` FOREIGN KEY (`kb_id`) REFERENCES `knowledgebase` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `media_asset` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `purpose` VARCHAR(20) NOT NULL  DEFAULT 'other',
    `filename` VARCHAR(255) NOT NULL,
    `content_type` VARCHAR(64) NOT NULL  DEFAULT 'image/jpeg',
    `size` INT NOT NULL  DEFAULT 0,
    `data_b64` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `owner_id` INT,
    CONSTRAINT `fk_media_as_user_27701c0d` FOREIGN KEY (`owner_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='上传的图片默认以 Base64 写入 data_b64。';
CREATE TABLE IF NOT EXISTS `shop_order` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `status` VARCHAR(20) NOT NULL  DEFAULT 'pending',
    `shipping_mode` VARCHAR(20) NOT NULL  DEFAULT 'instant',
    `address` VARCHAR(255) NOT NULL,
    `total` DECIMAL(10,2) NOT NULL  DEFAULT 0,
    `notes` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `store_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_shop_ord_store_624991c8` FOREIGN KEY (`store_id`) REFERENCES `store` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_shop_ord_user_c375a94a` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='商品订单：用户下单 → 商家履约 → 配送完成（一期无第三方支付）。';
CREATE TABLE IF NOT EXISTS `shop_orderitem` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `qty` INT NOT NULL  DEFAULT 1,
    `price` DECIMAL(10,2) NOT NULL  DEFAULT 0,
    `order_id` INT NOT NULL,
    `product_id` INT,
    CONSTRAINT `fk_shop_ord_shop_ord_37762209` FOREIGN KEY (`order_id`) REFERENCES `shop_order` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_shop_ord_product_e553cb1c` FOREIGN KEY (`product_id`) REFERENCES `product` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `pet` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(64) NOT NULL,
    `species` VARCHAR(20) NOT NULL  DEFAULT 'dog',
    `breed` VARCHAR(64),
    `gender` VARCHAR(10) NOT NULL  DEFAULT 'unknown',
    `birth_date` DATE,
    `weight_kg` DOUBLE,
    `chip_no` VARCHAR(64),
    `is_neutered` BOOL NOT NULL  DEFAULT 0,
    `nickname` VARCHAR(64) NOT NULL  DEFAULT '',
    `color` VARCHAR(64),
    `activity_level` VARCHAR(20) NOT NULL  DEFAULT 'medium',
    `diet` LONGTEXT NOT NULL,
    `allergies` LONGTEXT NOT NULL,
    `chronic_conditions` LONGTEXT NOT NULL,
    `temperament` VARCHAR(128),
    `living_env` VARCHAR(32) NOT NULL  DEFAULT 'indoor',
    `city` VARCHAR(64),
    `notes` LONGTEXT NOT NULL,
    `image_url` VARCHAR(500),
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `owner_id` INT NOT NULL,
    CONSTRAINT `fk_pet_user_040708a5` FOREIGN KEY (`owner_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='宠物档案：主人手动录入，AI 管家只读查询。';
CREATE TABLE IF NOT EXISTS `boardingreservation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `start_date` DATE NOT NULL,
    `end_date` DATE NOT NULL,
    `daily_fee` DECIMAL(10,2),
    `notes` LONGTEXT NOT NULL,
    `status` VARCHAR(20) NOT NULL  DEFAULT 'pending',
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `pet_id` INT NOT NULL,
    `store_id` INT,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_boarding_pet_c925ba16` FOREIGN KEY (`pet_id`) REFERENCES `pet` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_boarding_store_52d90797` FOREIGN KEY (`store_id`) REFERENCES `store` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_boarding_user_5b471433` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='寄养预订：按天排期。';
CREATE TABLE IF NOT EXISTS `medicalexam` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `exam_date` DATE NOT NULL,
    `hospital` VARCHAR(128),
    `items` VARCHAR(255),
    `result` LONGTEXT NOT NULL,
    `vet_name` VARCHAR(64),
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `pet_id` INT NOT NULL,
    CONSTRAINT `fk_medicale_pet_845659c0` FOREIGN KEY (`pet_id`) REFERENCES `pet` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='体检记录：可空展示「未做体检」。';
CREATE TABLE IF NOT EXISTS `medicationrecord` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `drug_name` VARCHAR(128) NOT NULL,
    `start_date` DATE,
    `end_date` DATE,
    `dosage` VARCHAR(128),
    `reason` VARCHAR(255),
    `notes` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `pet_id` INT NOT NULL,
    CONSTRAINT `fk_medicati_pet_64f25849` FOREIGN KEY (`pet_id`) REFERENCES `pet` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='用药记录：可空展示「未使用药物」。';
CREATE TABLE IF NOT EXISTS `trainerprofile` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `display_name` VARCHAR(64) NOT NULL,
    `city` VARCHAR(64),
    `specialties` VARCHAR(255) NOT NULL  DEFAULT '',
    `years` INT NOT NULL  DEFAULT 1,
    `price_from` DECIMAL(10,2),
    `service_mode` VARCHAR(20) NOT NULL  DEFAULT 'both',
    `bio` LONGTEXT NOT NULL,
    `avatar_url` VARCHAR(500),
    `experience` LONGTEXT NOT NULL,
    `cert_note` LONGTEXT NOT NULL,
    `proof_images` LONGTEXT NOT NULL,
    `verified` BOOL NOT NULL  DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_trainerp_user_b2802f84` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='训犬师主页：平台审核后对外展示；经历与证明图用于建立信任。';
CREATE TABLE IF NOT EXISTS `appointment` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `appt_type` VARCHAR(20) NOT NULL  DEFAULT 'exam',
    `appt_time` DATETIME(6) NOT NULL,
    `status` VARCHAR(20) NOT NULL  DEFAULT 'pending',
    `notes` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `pet_id` INT,
    `store_id` INT,
    `trainer_id` INT,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_appointm_pet_397bdefa` FOREIGN KEY (`pet_id`) REFERENCES `pet` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_appointm_store_d431f3ac` FOREIGN KEY (`store_id`) REFERENCES `store` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_appointm_trainerp_2d5d6617` FOREIGN KEY (`trainer_id`) REFERENCES `trainerprofile` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_appointm_user_cf7c35b0` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='预约：门店就诊/美容/寄养咨询，或训犬师训练课时。';
CREATE TABLE IF NOT EXISTS `lead` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `need_type` VARCHAR(20) NOT NULL  DEFAULT 'consult',
    `summary` LONGTEXT NOT NULL,
    `city` VARCHAR(64),
    `budget` DOUBLE,
    `status` VARCHAR(20) NOT NULL  DEFAULT 'open',
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `matched_store_id` INT,
    `matched_trainer_id` INT,
    `operator_id` INT,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_lead_store_df2623a9` FOREIGN KEY (`matched_store_id`) REFERENCES `store` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_lead_trainerp_d9615776` FOREIGN KEY (`matched_trainer_id`) REFERENCES `trainerprofile` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_lead_user_dbe76980` FOREIGN KEY (`operator_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_lead_user_cb1042bc` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='用户需求线索：运营者获客与资源匹配的工作单。';
CREATE TABLE IF NOT EXISTS `vaccinerecord` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `vaccine_name` VARCHAR(64) NOT NULL,
    `dose_no` INT NOT NULL  DEFAULT 1,
    `vaccinated_at` DATE NOT NULL,
    `next_due_date` DATE,
    `notes` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `pet_id` INT NOT NULL,
    CONSTRAINT `fk_vacciner_pet_bfda798b` FOREIGN KEY (`pet_id`) REFERENCES `pet` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='疫苗记录：主人手动录入，next_due_date 用于到期提醒。';
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;

"""


async def upgrade(db: BaseDBAsyncClient) -> str:
    """创建当前模型对应的表；旧库缺列时追加 ALTER。不删除数据。"""
    extra = await pending_legacy_statements(db)
    return assemble_upgrade_sql(CREATE_SQL, extra)


async def downgrade(db: BaseDBAsyncClient) -> str:
    """禁止自动回滚。DROP TABLE 会清空演示数据。"""
    del db
    raise RuntimeError(
        "已禁止初始迁移自动 downgrade：回滚会删除全部业务表并清空演示数据。"
        "如确需重建，请先备份数据库再手工处理。"
    )

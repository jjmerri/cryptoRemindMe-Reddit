DROP SCHEMA IF EXISTS xrp_remind_me;
CREATE SCHEMA xrp_remind_me;
USE xrp_remind_me;

CREATE TABLE `comment_list` (
  `list` longtext,
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 ;

CREATE TABLE `message_date` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `object_name` varchar(400) NOT NULL DEFAULT '',
  `message` varchar(11000) DEFAULT NULL,
  `new_price` DECIMAL(12,6) DEFAULT NULL,
  `origin_price` DECIMAL(12,6) DEFAULT NULL,
  `userID` varchar(50) DEFAULT NULL,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_date` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `permalink` varchar(400) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

INSERT INTO comment_list (list) VALUES ('');

DROP SCHEMA IF EXISTS crypto_remind_me;
CREATE SCHEMA crypto_remind_me;
USE crypto_remind_me;

CREATE TABLE `comment_list` (
  `list` longtext,
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 ;

CREATE TABLE `reminder` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `object_name` varchar(400) NOT NULL,
  `message` varchar(11000) DEFAULT NULL,
  `new_price` DECIMAL(18,9),
  `origin_price` DECIMAL(18,9),
  `userID` varchar(50),
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_date` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `permalink` varchar(400) NOT NULL,
  `ticker` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

INSERT INTO comment_list (list) VALUES ('''''');

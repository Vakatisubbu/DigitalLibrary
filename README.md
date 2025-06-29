Python installation on the AWS EC2 Linux machine (Kernel version 5.10)

sudo yum install python3-pip git -y

sudo pip3 install flask

sudo pip3 install mysql-connector-python

sudo pip3 install requests

Database Schema creaion:
CREATE DATABASE IF NOT EXISTS digital_library; USE digital_library;

CREATE TABLE IF NOT EXISTS users ( id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL, mobile VARCHAR(20) NOT NULL, email VARCHAR(100) NOT NULL UNIQUE, password VARCHAR(255) NOT NULL, gender VARCHAR(10), location VARCHAR(100), image VARCHAR(255) );

CREATE TABLE IF NOT EXISTS books ( id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(255) NOT NULL, author VARCHAR(255), available BOOLEAN DEFAULT TRUE );

CREATE TABLE IF NOT EXISTS history ( id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, book_id INT, borrow_date DATETIME, return_date DATETIME, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE );

INSERT INTO books (title, author, available) VALUES ('Wings of Fire', 'A.P.J. Abdul Kalam', TRUE), ('The Guide', 'R.K. Narayan', TRUE), ('Godan', 'Munshi Premchand', TRUE), ('Train to Pakistan', 'Khushwant Singh', TRUE), ('Ignited Minds', 'A.P.J. Abdul Kalam', TRUE), ('Mahabharata', 'Ved Vyasa', TRUE), ('Python Crash Course', 'Eric Matthes', TRUE), ('Digital Fortress', 'Dan Brown', TRUE), ('You Can Win', 'Shiv Khera', TRUE), ('Zero to One', 'Peter Thiel', TRUE);

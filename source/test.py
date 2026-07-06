from config import AppConfig

AppConfig.create_default_config_file()
conf = AppConfig.create_from_file()
conf.start_url = "github.com"
conf.save_to_file()
print(conf)
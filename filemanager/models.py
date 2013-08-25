from django.db import models
import thumbnailer.thumbnailer

# Create your models here.

class filename(models.Model):

    post = models.ForeignKey(Post,)
    filename = models.FileField(upload_to="uploads/"+post.title)
    thumbnailpath = models.CharField(max_length=256, blank=True, null=True)
    filetype = models.CharField(max_length=8, blank=True, null=True)
    def save(self):
        thumbnaildata = thumbnailer.thumbnailer.thumbnail(self.filename,(200,200), forceupdate=True)
        self.thumbnailpath = thumbnaildata[0]
        self.filetype = thumbnaildata[2]
        super(filename, self).save()
